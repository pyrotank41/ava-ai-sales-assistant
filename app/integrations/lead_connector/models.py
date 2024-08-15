# Define an Enum for message types
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl


# class LCMessageType(
#     int, Enum
# ):  # the type we get from the leadconnector get all message api
#     TYPE_CALL = 1
#     TYPE_SMS = 2
#     TYPE_EMAIL = 3
#     TYPE_FACEBOOK = 4
#     TYPE_GMB = 5
#     TYPE_INSTAGRAM = 6
#     TYPE_WHATSAPP = 7
#     TYPE_ACTIVITY_CONTACT = 8
#     TYPE_ACTIVITY_INVOICE = 9
#     TYPE_ACTIVITY_PAYMENT = 10
#     TYPE_ACTIVITY_OPPORTUNITY = 11
#     TYPE_LIVE_CHAT = 12
#     TYPE_ACTIVITY_APPOINTMENT = 13

class LCMessageType(Enum):
    TYPE_CALL = "TYPE_CALL"
    TYPE_SMS = "TYPE_SMS"
    TYPE_EMAIL = "TYPE_EMAIL"
    TYPE_SMS_REVIEW_REQUEST = "TYPE_SMS_REVIEW_REQUEST"
    TYPE_WEBCHAT = "TYPE_WEBCHAT"
    TYPE_SMS_NO_SHOW_REQUEST = "TYPE_SMS_NO_SHOW_REQUEST"
    TYPE_CAMPAIGN_SMS = "TYPE_CAMPAIGN_SMS"
    TYPE_CAMPAIGN_CALL = "TYPE_CAMPAIGN_CALL"
    TYPE_CAMPAIGN_EMAIL = "TYPE_CAMPAIGN_EMAIL"
    TYPE_CAMPAIGN_VOICEMAIL = "TYPE_CAMPAIGN_VOICEMAIL"
    TYPE_FACEBOOK = "TYPE_FACEBOOK"
    TYPE_CAMPAIGN_FACEBOOK = "TYPE_CAMPAIGN_FACEBOOK"
    TYPE_CAMPAIGN_MANUAL_CALL = "TYPE_CAMPAIGN_MANUAL_CALL"
    TYPE_CAMPAIGN_MANUAL_SMS = "TYPE_CAMPAIGN_MANUAL_SMS"
    TYPE_GMB = "TYPE_GMB"
    TYPE_CAMPAIGN_GMB = "TYPE_CAMPAIGN_GMB"
    TYPE_REVIEW = "TYPE_REVIEW"
    TYPE_INSTAGRAM = "TYPE_INSTAGRAM"
    TYPE_WHATSAPP = "TYPE_WHATSAPP"
    TYPE_CUSTOM_SMS = "TYPE_CUSTOM_SMS"
    TYPE_CUSTOM_EMAIL = "TYPE_CUSTOM_EMAIL"
    TYPE_CUSTOM_PROVIDER_SMS = "TYPE_CUSTOM_PROVIDER_SMS"
    TYPE_CUSTOM_PROVIDER_EMAIL = "TYPE_CUSTOM_PROVIDER_EMAIL"
    TYPE_IVR_CALL = "TYPE_IVR_CALL"
    TYPE_ACTIVITY_CONTACT = "TYPE_ACTIVITY_CONTACT"
    TYPE_ACTIVITY_INVOICE = "TYPE_ACTIVITY_INVOICE"
    TYPE_ACTIVITY_PAYMENT = "TYPE_ACTIVITY_PAYMENT"
    TYPE_ACTIVITY_OPPORTUNITY = "TYPE_ACTIVITY_OPPORTUNITY"
    TYPE_LIVE_CHAT = "TYPE_LIVE_CHAT"
    TYPE_LIVE_CHAT_INFO_MESSAGE = "TYPE_LIVE_CHAT_INFO_MESSAGE"
    TYPE_ACTIVITY_APPOINTMENT = "TYPE_ACTIVITY_APPOINTMENT"
    TYPE_FACEBOOK_COMMENT = "TYPE_FACEBOOK_COMMENT"
    TYPE_INSTAGRAM_COMMENT = "TYPE_INSTAGRAM_COMMENT"
    TYPE_CUSTOM_CALL = "TYPE_CUSTOM_CALL"
    TYPE_ACTIVITY = "TYPE_ACTIVITY"


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
    type: int
    messageType: LCMessageType
    attachments: Optional[List[HttpUrl]] = []
    body: str = ""
    contentType: str = ""
    dateAdded: Optional[datetime] = None
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
    status: Optional[str] = None
    message: Optional[str] = None
    code: Optional[str] = None


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


class LCCustomFieldModelType(str, Enum):
    CONTACT = "contact"
    OPPORTUNITY = "opportunity"


class LCCustomField(BaseModel):
    id: str = Field(..., example="3sv6UEo51C9Bmpo1cKTq")
    name: str = Field(..., example="pincode")
    fieldKey: Optional[str] = Field(None, example="contact.pincode")
    placeholder: Optional[str] = Field(None, example="Pin code")
    dataType: Optional[str] = Field(None, example="TEXT")
    position: Optional[int] = Field(None, example=0)
    picklistOptions: Optional[List[str]] = Field(None, example=["first option"])
    picklistImageOptions: Optional[List[str]] = Field(default_factory=list)
    isAllowedCustomOption: Optional[bool] = Field(None, example=False)
    isMultiFileAllowed: Optional[bool] = Field(None, example=True)
    maxFileLimit: Optional[int] = Field(None, example=4)
    locationId: Optional[str] = Field(None, example="3sv6UEo51C9Bmpo1cKTq")
    model: Optional[LCCustomFieldModelType] = Field(
        None, example=LCCustomFieldModelType.OPPORTUNITY
    )
    # class Config:
    #     use_enum_values = True


class LCCustomFieldMinimal(BaseModel):
    id: str
    value: Optional[Any] = None


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
    customFields: Optional[List[LCCustomFieldMinimal]] = list()
    businessId: Optional[str] = None
    attributionSource: Optional[AttributionSource] = None
    lastAttributionSource: Optional[AttributionSource] = None
    additionalEmails: Optional[List[str]] = None
    additionalPhones: Optional[List[str]] = None


class LCContactResponse(BaseModel):
    contact: LCContactInfo
