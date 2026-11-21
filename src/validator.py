from typing import Optional

from pydantic import BaseModel, Field, field_validator


class UserProfile(BaseModel):
    age: Optional[int] = Field(default=None, ge=0, le=120)
    state: Optional[str] = None
    district: Optional[str] = None
    native_place: Optional[str] = None
    native_language: Optional[str] = None
    annual_income: Optional[float] = Field(default=None, ge=0)
    occupation: Optional[str] = None
    education: Optional[str] = None
    gender: Optional[str] = None
    category: Optional[str] = None
    is_farmer: Optional[bool] = None
    is_pregnant: Optional[bool] = None
    is_first_pregnancy: Optional[bool] = None
    is_govt_school_student: Optional[bool] = None
    has_disability: Optional[bool] = None
    residence_type: Optional[str] = None
    bpl: Optional[bool] = None

    @field_validator(
        "state",
        "district",
        "native_place",
        "native_language",
        "occupation",
        "education",
        "gender",
        "category",
        "residence_type",
    )
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return None
        value = value.strip()
        return value or None
