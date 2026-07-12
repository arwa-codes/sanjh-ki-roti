import random
import string
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.customer import Customer
from app.models.billing import Referral
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.repositories.customer import customer_repository
from app.repositories.billing import referral_repository
from app.core.exceptions import EntityNotFoundException, EntityAlreadyExistsException

class CustomerService:
    def create_customer_profile(
        self, db: Session, user_id: UUID, customer_in: CustomerCreate
    ) -> Customer:
        """Create a profile for an authenticated user and process any referral codes."""
        # Check if profile already exists for user
        if customer_repository.get_by_user_id(db, user_id=user_id):
            raise EntityAlreadyExistsException("Profile already exists for this user.")
        
        # Enforce unique Aadhaar number check
        if customer_repository.get_by_aadhaar(db, aadhaar_number=customer_in.aadhaar_number):
            raise EntityAlreadyExistsException("A profile with this Aadhaar number already exists.")

        # Generate unique referral code: REF-[first 6 chars of user UUID]-[3 random uppercase letters]
        suffix = "".join(random.choices(string.ascii_uppercase, k=3))
        ref_code = f"REF-{str(user_id)[:6].upper()}-{suffix}"

        # Resolve referring customer if code is provided
        referred_by_customer = None
        if customer_in.referral_code:
            referred_by_customer = customer_repository.get_by_referral_code(
                db, referral_code=customer_in.referral_code
            )
            if not referred_by_customer:
                raise EntityNotFoundException("Referral code is invalid.")

        # Create Customer record
        customer_data = {
            "user_id": user_id,
            "first_name": customer_in.first_name,
            "last_name": customer_in.last_name,
            "address": customer_in.address,
            "pincode": customer_in.pincode,
            "aadhaar_number": customer_in.aadhaar_number,
            "referral_code": ref_code,
            "referred_by_id": referred_by_customer.id if referred_by_customer else None,
            "is_verified": False
        }
        customer = customer_repository.create(db, obj_in=customer_data)

        # Log pending referral relationship if referred by another customer
        if referred_by_customer:
            referral_data = {
                "referrer_id": referred_by_customer.id,
                "referee_id": customer.id,
                "discount_applied": 100.00,  # Promotional discount of Rs 100
                "status": "pending"
            }
            referral_repository.create(db, obj_in=referral_data)

        return customer

    def upload_aadhaar_document(
        self, db: Session, customer_id: UUID, file_content: bytes, filename: str
    ) -> str:
        """Mock upload of Aadhaar document, verifying mime-type structure."""
        customer = customer_repository.get(db, id=customer_id)
        if not customer:
            raise EntityNotFoundException("Customer profile not found.")
            
        # Basic validation: ensure file is PDF/JPEG/PNG and not exceeding 5MB
        ext = filename.split(".")[-1].lower()
        if ext not in ["pdf", "jpg", "jpeg", "png"]:
            raise ValueError("Invalid document type. Allowed types are PDF, JPG, JPEG, PNG.")
            
        if len(file_content) > 5 * 1024 * 1024:
            raise ValueError("File exceeds maximum allowed size of 5MB.")

        # Mock S3 uploading file path URL
        mock_url = f"https://mock-s3-bucket.s3.amazonaws.com/uploads/aadhaar/{customer_id}.{ext}"
        
        # Update customer profile url
        customer_repository.update(db, db_obj=customer, obj_in={"document_url": mock_url})
        return mock_url

    def verify_customer(self, db: Session, customer_id: UUID, is_verified: bool) -> Customer:
        """Mark a customer's document verification status (Admin capability)."""
        customer = customer_repository.get(db, id=customer_id)
        if not customer:
            raise EntityNotFoundException("Customer profile not found.")
            
        return customer_repository.update(db, db_obj=customer, obj_in={"is_verified": is_verified})

# Global customer service instance
customer_service = CustomerService()
