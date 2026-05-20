from nano_orm import database

class Field:
    """Base class for all ORM fields"""
    sql_type = ""

    def __init__(self, required=False):
        self.required = required
        self.name = None

    def __set__(self, instance, value):
        if not instance:
            return

        if self.required and not value:
            raise ValueError(f"field '{self.name}' is mandatory")

        self.validate(value)

        instance.__dict__[self.name] = value

    def __get__(self, instance, owner):
        if not instance:
            return self

        return instance.__dict__.get(self.name, None)

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

    @classmethod
    def create_table(cls):
        """Generate SQL query to create table in DB"""
        columns = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
        
        for field_name, field_object in cls._fields.items():
            definition = f"{field_name} {field_object.sql_type}"
            if field_object.required:
                definition += " NOT NULL"
            columns.append(definition)

        query = f"CREATE TABLE IF NOT EXISTS {cls._table} ({', '.join(columns)});"

        connection = database.get_connection()
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()
        connection.close()

    @classmethod
    def create(cls, **kwargs):
        """Create a new reccord in DB"""
        fields_to_insert = []
        values = []
        placeholders = []

        for key, value in kwargs.items():
            if key in cls._fields:
                cls._fields[key].validate(value)
                fields_to_insert.append(key)
                values.append(value)
                placeholders.append("?")

        if not fields_to_insert:
            raise ValueError("No valid fields provided")

        colums_str = ", ".join(fields_to_insert)
        placeholders_str = ", ".join(placeholders)
        query = f"INSERT INTO {cls._table} {colums_str} VALUE ({placeholders_str});"

        connection = database.get_connection()
        cursor = connection.cursor()
        cursor.execute(query, values)

        generated_id = cursor.lastrowid

        connection.commit()
        connection.close()

        instance = cls(**kwargs)
        instance.id = generated_id


