"""SQLModel base model with shared conventions.

Each table model defines its own id, created_at, updated_at directly
to avoid SQLModel Field + sa_column conflicts with inheritance.
"""

from sqlmodel import SQLModel

# Base class for all database tables — provides SQLModel functionality only
# No shared columns to avoid inheritance conflicts with sa_column
BaseModel = SQLModel
