# Define an Enum for message types
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, EmailStr, HttpUrl


class LCMessageType(
    int, Enum
):  # the type we get from the leadconnector get all message api
    TYPE_CALL = 1
    TYPE_SMS = 2
    TYPE_EMAIL = 3
    TYPE_FACEBOOK = 4
    TYPE_GMB = 5
    TYPE_INSTAGRAM = 6
    TYPE_WHATSAPP = 7
    TYPE_ACTIVITY_CONTACT = 8
    TYPE_ACTIVITY_INVOICE = 9
    TYPE_ACTIVITY_PAYMENT = 10
    TYPE_ACTIVITY_OPPORTUNITY = 11
    TYPE_LIVE_CHAT = 12
    TYPE_ACTIVITY_APPOINTMENT = 13


class LCMessageStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    UNDELIVERED = "undelivered"
    CONNECTED = "connected"
    FAILED = "failed"
    OPENED = "opened"


class LCMessageDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class LCMessage(BaseModel):
    id: str
    direction: Optional[LCMessageDirection] = None
    status: Optional[LCMessageStatus] = None
    type: LCMessageType
    attachments: Optional[List[HttpUrl]] = []
    body: str = ""
    contentType: str = ""
    dateAdded: datetime
    userId: Optional[str] = None
    source: Optional[str] = None

    def model_dump(self, **kwargs):
        # Convert the datetime to a string
        data = super().model_dump()
        data["dateAdded"] = self.dateAdded.isoformat()
        data["attachments"] = [str(url) if url else None for url in self.attachments]
        return data


class LeadConnectorConfig(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str
    scope: list[str]
    user_type: str
    company_id: str
    location_id: str
    user_id: str
    token_expiry: datetime = None  # To track token expiry time


class DNDSettings(BaseModel):
    status: str
    message: str
    code: str


class AttributionSource(BaseModel):
    url: Optional[str] = None
    campaign: Optional[str] = None
    utmSource: Optional[str] = None
    utmMedium: Optional[str] = None
    utmContent: Optional[str] = None
    referrer: Optional[str] = None
    campaignId: Optional[str] = None
    fbclid: Optional[str] = None
    gclid: Optional[str] = None
    msclikid: Optional[str] = None
    dclid: Optional[str] = None
    fbc: Optional[str] = None
    fbp: Optional[str] = None
    fbEventId: Optional[str] = None
    userAgent: Optional[str] = None
    ip: Optional[str] = None
    medium: Optional[str] = None
    mediumId: Optional[str] = None


class CustomField(BaseModel):
    id: str
    value: str


class LCContactInfo(BaseModel):
    id: str
    name: Optional[str] = None
    locationId: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[EmailStr] = None
    emailLowerCase: Optional[EmailStr] = None
    timezone: Optional[str] = None
    companyName: Optional[str] = None
    phone: Optional[str] = None
    dnd: Optional[bool] = None
    dndSettings: Optional[Dict[str, DNDSettings]] = None
    type: Optional[str] = None
    source: Optional[str] = None
    assignedTo: Optional[str] = None
    address1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postalCode: Optional[str] = None
    website: Optional[HttpUrl] = None
    tags: Optional[List[str]] = None
    dateOfBirth: Optional[str] = None
    dateAdded: Optional[str] = None
    dateUpdated: Optional[str] = None
    attachments: Optional[List[str]] = None
    ssn: Optional[str] = None
    gender: Optional[str] = None
    keyword: Optional[str] = None
    firstNameLowerCase: Optional[str] = None
    fullNameLowerCase: Optional[str] = None
    lastNameLowerCase: Optional[str] = None
    lastActivity: Optional[str] = None
    customFields: Optional[List[CustomField]] = None
    businessId: Optional[str] = None
    attributionSource: Optional[AttributionSource] = None
    lastAttributionSource: Optional[AttributionSource] = None
    additionalEmails: Optional[List[str]] = None
    additionalPhones: Optional[List[str]] = None


class ContactResponse(BaseModel):
    contact: LCContactInfo
