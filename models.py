"""Inputs shared by the Responses and Chat Completions endpoints."""
import pycountry
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')

    message: str = Field(min_length=1, max_length=4000, examples=['What is the weather in Auckland, New Zealand?'])
    city: str = Field(min_length=2, max_length=120, examples=['Auckland'])
    country: str = Field(min_length=2, max_length=100, examples=['NZ'])
    region: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator('country')
    @classmethod
    def normalize_country(cls, value: str) -> str:
        try:
            return pycountry.countries.lookup(value).alpha_2
        except LookupError:
            raise ValueError('Use a country name or ISO code, such as New Zealand, NZ, Australia, or AU.') from None


class RegularChatRequest(BaseModel):
    """One general question, without location or weather inputs."""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')

    message: str = Field(min_length=1, max_length=4000, examples=['Explain Python in simple terms.'])
