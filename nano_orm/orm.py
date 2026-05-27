from nano_orm import database

def get_model_by_name(model_name):
    if not isinstance(model_name, str):
        return model_name
    
    for subclass in BaseModel.__subclasses__():
        if subclass.__name__ == model_name:
            return subclass
    raise ValueError(f"Model '{model_name}' has not been found.")

class Field:
    """Base class for all ORM fields"""
    sql_type = None

    def __init__(self, required=False):
        self.required = required
        self.name = None

    def __set__(self, instance, value):
        if not instance:
            return

        if self.required and not value:
            raise ValueError(f"field '{self.name}' is mandatory")

        self.validate(value)
        instance.__dict__[f"_{self.name}"] = value

    def __get__(self, instance, owner):
        if not instance:
            return self

        return instance.__dict__.get(f"_{self.name}", None)

    def validate(self, value):
        """Override to validate data"""
        pass

class CharField(Field):
    sql_type = "TEXT"

    def validate(self, value):
        if value and not isinstance(value, str):
            raise TypeError(f"field '{self.name} must be a string")

class IntegerField(Field):
    sql_type = "INTEGER"

    def validate(self, value):
        if value and not isinstance(value, int):
            raise TypeError(f"field '{self.name} must be an integer")


class BelongsTo(Field):
    sql_type = "INTEGER"

    def __init__(self, related_model, required=False):
        super().__init__(required=required)
        self.related_model_init = related_model

    # to avoid circular reference, as child/parent does not know either at creation
    @property
    def related_model(self):
        return get_model_by_name(self.related_model_init)

    def validate(self, value):
        if value and not isinstance(value, int):
            raise ValueError(f"Foreign key '{self.name}' must be an integer (got {type(value).__name__})")

    def __get__(self, instance, owner):
        if not instance:
            return self

        raw_id = instance.__dict__.get(f"_{self.name}_id")
        if not raw_id:
            return None

        return self.related_model.get(raw_id)

    def __set__(self, instance, value):
        if instance is None:
            return

        # if is a foreign key
        if hasattr(value, "id"):
            db_value = value.id
        else:
            db_value = value

        self.validate(db_value)

        instance.__dict__[f"_{self.name}_id"] = db_value


class HasMany(Field):
    """Virtual field with no SQL counterpart"""

    def __init__(self, related_model, foreign_key_name):
        self.related_model_init = related_model
        self.foreign_key_name = foreign_key_name
        self.name = None

    @property
    def related_model(self):
        return get_model_by_name(self.related_model_init)

    def __get__(self, instance, owner):
        if not instance:
            return self

        if not instance.id:
            return []

        query_kwargs = {self.foreign_key_name: instance} # Child.search(target=parent)
        return self.related_model.search(**query_kwargs)

    def __set__(self, instance, value):
        raise AttributeError("Cannot alter relation direclty, update related model instance instead")


class MetaModel(type):
    def __new__(cls, name, bases, attrs):

        if name == "BaseModel":
            return super().__new__(cls, name, bases, attrs)

        fields = {}

        for key, value in attrs.items():
            if isinstance(value, Field):
                value.name = key
                fields[key] = value

        attrs["_fields"] = fields
        attrs["_table"] = name.lower()

        return super().__new__(cls, name, bases, attrs)

class BaseModel(metaclass=MetaModel):
    def __init__(self, **kwargs):
        self.id = None
        for key, value in kwargs.items():
            if key in self._fields:
                setattr(self, key, value)

    def __repr__(self):
        pretty_print = f"{self.__class__.__name__}(id={self.id})\n"
        for key, field in self._fields.items():
            val = getattr(self, key)
            pretty_print += f"  - {key}: {val}\n"
        return pretty_print

    @classmethod
    def create_table(cls):
        """Generate SQL query to create table in DB"""
        columns = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
        foreign_keys = []

        for field_name, field_object in cls._fields.items():

            # Bypass HasMany fields
            if not getattr(field_object, "sql_type", None):
                continue

            db_col = f"{field_name}_id" if isinstance(field_object, BelongsTo) else field_name
            definition = f"{db_col} {field_object.sql_type}"
            if field_object.required:
                definition += " NOT NULL"
            columns.append(definition)

            if isinstance(field_object, BelongsTo):
                target_table = field_object.related_model._table
                fk_def = f"FOREIGN KEY ({db_col}) REFERENCES {target_table}(id) ON DELETE CASCADE"
                foreign_keys.append(fk_def)


        all_definitions = columns + foreign_keys
        query = f"CREATE TABLE IF NOT EXISTS {cls._table} ({', '.join(all_definitions)});"

        connection = database.get_connection()
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()
        connection.close()

    @classmethod
    def create(cls, **kwargs):
        """Create a new record in DB"""
        instance = cls(**kwargs)
        fields_to_insert = []
        values = []
        placeholders = []

        for key, field_object in cls._fields.items():
            # Bypass HasMany
            if not getattr(field_object, "sql_type", None):
                continue

            internal_key = f"_{key}_id" if isinstance(field_object, BelongsTo) else f"_{key}"
            db_col = f"{key}_id" if isinstance(field_object, BelongsTo) else key

            if internal_key in instance.__dict__:
                fields_to_insert.append(db_col)
                values.append(instance.__dict__[internal_key])
                placeholders.append("?")

        if not fields_to_insert:
            raise ValueError("No valid fields provided")

        columns_str = ", ".join(fields_to_insert)
        placeholders_str = ", ".join(placeholders)
        query = f"INSERT INTO {cls._table} ({columns_str}) VALUES ({placeholders_str});"

        connection = database.get_connection()
        cursor = connection.cursor()
        cursor.execute(query, values)

        generated_id = cursor.lastrowid

        connection.commit()
        connection.close()

        instance.id = generated_id
        return instance

    @classmethod
    def search(cls, **kwargs):
        """Fetch records from DB and map them to Python objects"""
        
        physical_fields = []
        for key, field_object in cls._fields.items():
            # All but virtual fiels
            if getattr(field_object, "sql_type", None):
                physical_fields.append(key)

        # field name for sql query, add _id suffix when foreign key
        sql_cols = ["id"]
        for key in physical_fields:
            if isinstance(cls._fields[key], BelongsTo):
                sql_cols.append(f"{key}_id")
            else:
                sql_cols.append(key)

        query = f"SELECT {', '.join(sql_cols)} FROM {cls._table}"
        values = []
        
        # Where clause
        if kwargs:
            filters = []
            for key, value in kwargs.items():
                if key == "id":
                    filters.append("id = ?")
                    values.append(value)
                elif key in cls._fields:
                    if isinstance(cls._fields[key], BelongsTo):
                        filters.append(f"{key}_id = ?")
                        values.append(value.id if hasattr(value, "id") else value)
                    else:
                        filters.append(f"{key} = ?")
                        values.append(value)

            if filters:
                query += " WHERE " + " AND ".join(filters)

        query += ";"

        connection = database.get_connection()
        cursor = connection.cursor()
        cursor.execute(query, values)
        rows = cursor.fetchall()
        connection.close()

        # SQL to Python object
        instances = []
        for row in rows:
            instance = cls()
            instance.id = row[0]
            
            for index, key in enumerate(physical_fields):
                field_object = cls._fields[key]
                if isinstance(field_object, BelongsTo):
                    instance.__dict__[f"_{key}_id"] = row[index + 1]
                else:
                    instance.__dict__[f"_{key}"] = row[index + 1]

            instances.append(instance)

        return instances

    @classmethod
    def get(cls, record_id):
        """Fetch and return the object associated with this id"""
        result = cls.search(id=record_id)
        return result[0] if result else None



    def update(self, **kwargs):
        """Update fields from existing record"""
        if not self.id:
            raise ValueError("Object ID not found")

        fields_to_update = []
        values = []
        
        for key, value in kwargs.items():
            if key not in self._fields or not getattr(self._fields[key], "sql_type", None):
                continue

            setattr(self, key, value)

            if isinstance(self._fields[key], BelongsTo):
                db_col = f"{key}_id"
                db_value = self.__dict__[f"_{key}_id"]
            else:
                db_col = key
                db_value = self.__dict__[f"_{key}"]

            fields_to_update.append(f"{db_col} = ?")
            values.append(db_value)

        if not fields_to_update:
            return False

        fields_str = ", ".join(fields_to_update)
        query = f"UPDATE {self._table} SET {fields_str} WHERE id = ?"
        values.append(self.id)
        
        connection = database.get_connection()
        cursor = connection.cursor()
        cursor.execute(query, values)
        connection.commit()
        connection.close()

        return True

    def delete(self):
        """Delete reccord + cascade delete for 1-N relations """
        if not self.id:
            raise ValueError("Object ID not found")

        query = f"DELETE FROM {self._table} WHERE id = ?"

        connection = database.get_connection()
        cursor = connection.cursor()
        cursor.execute(query, [self.id])
        connection.commit()
        connection.close()

        self.id = None

        return True













