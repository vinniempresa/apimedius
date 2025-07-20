"""
Brazilian PIX Payment System
Generates real, authentic PIX codes following BR Code (EMVCo) standard
"""
import uuid
import qrcode
import base64
from io import BytesIO
from datetime import datetime, timedelta
import hashlib

class BrazilianPixGenerator:
    """Generates authentic Brazilian PIX codes following EMVCo standard"""
    
    def __init__(self):
        self.merchant_name = "RECEITA FEDERAL"
        self.merchant_city = "BRASILIA"
        self.currency_code = "986"  # BRL
        self.country_code = "BR"
        
    def _generate_transaction_id(self):
        """Generate unique transaction ID for PIX"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = uuid.uuid4().hex[:8].upper()
        return f"REC{timestamp}{random_part}"
    
    def _calculate_crc16_ccitt(self, data: str) -> str:
        """Calculate CRC16-CCITT for PIX code validation"""
        crc = 0xFFFF
        for byte in data.encode('utf-8'):
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return f"{crc:04X}"
    
    def _format_emv_field(self, tag: str, value: str) -> str:
        """Format EMV field with tag-length-value structure"""
        length = f"{len(value):02d}"
        return f"{tag}{length}{value}"
    
    def generate_pix_code(self, amount: float, recipient_key: str, recipient_name: str, 
                         transaction_id: str = None, description: str = "") -> str:
        """
        Generate authentic Brazilian PIX code following EMVCo BR Code standard
        
        Args:
            amount: Payment amount in BRL
            recipient_key: PIX key (email, phone, CPF, or random key)
            recipient_name: Recipient name
            transaction_id: Optional transaction ID
            description: Optional payment description
            
        Returns:
            Complete PIX code string
        """
        if not transaction_id:
            transaction_id = self._generate_transaction_id()
            
        # Build PIX code following EMVCo standard
        pix_code = ""
        
        # Payload Format Indicator (00)
        pix_code += self._format_emv_field("00", "01")
        
        # Point of Initiation Method (01) - static QR code
        pix_code += self._format_emv_field("01", "12")
        
        # Merchant Account Information (26) - PIX
        merchant_info = ""
        merchant_info += self._format_emv_field("00", "br.gov.bcb.pix")
        merchant_info += self._format_emv_field("01", recipient_key)
        if description:
            merchant_info += self._format_emv_field("02", description[:25])  # Limit description
        pix_code += self._format_emv_field("26", merchant_info)
        
        # Merchant Category Code (52) - Generic
        pix_code += self._format_emv_field("52", "0000")
        
        # Transaction Currency (53) - BRL
        pix_code += self._format_emv_field("53", self.currency_code)
        
        # Transaction Amount (54) - Only if amount > 0
        if amount > 0:
            amount_str = f"{amount:.2f}"
            pix_code += self._format_emv_field("54", amount_str)
        
        # Country Code (58)
        pix_code += self._format_emv_field("58", self.country_code)
        
        # Merchant Name (59)
        pix_code += self._format_emv_field("59", recipient_name[:25])
        
        # Merchant City (60)
        pix_code += self._format_emv_field("60", self.merchant_city[:15])
        
        # Additional Data Field Template (62) - Transaction ID
        additional_data = ""
        additional_data += self._format_emv_field("05", transaction_id[:25])
        pix_code += self._format_emv_field("62", additional_data)
        
        # CRC16 (63) - calculated after all other fields
        pix_code += "6304"
        crc = self._calculate_crc16_ccitt(pix_code)
        pix_code += crc
        
        return pix_code
    
    def generate_qr_code_image(self, pix_code: str) -> str:
        """
        Generate QR code image for PIX code
        
        Args:
            pix_code: Complete PIX code string
            
        Returns:
            Base64 encoded QR code image as data URL
        """
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(pix_code)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_data = buffer.getvalue()
        img_base64 = base64.b64encode(img_data).decode()
        
        return f"data:image/png;base64,{img_base64}"
    
    def create_pix_payment(self, amount: float, customer_name: str, customer_cpf: str, 
                          customer_email: str = "gerarpagamento@gmail.com") -> dict:
        """
        Create complete PIX payment with code and QR code
        
        Args:
            amount: Payment amount in BRL
            customer_name: Customer name
            customer_cpf: Customer CPF
            customer_email: Customer email
            
        Returns:
            Dictionary with PIX payment data
        """
        transaction_id = self._generate_transaction_id()
        
        # Use customer email as PIX key (most common for businesses)
        pix_key = customer_email
        description = "Receita de bolo"
        
        # Generate PIX code
        pix_code = self.generate_pix_code(
            amount=amount,
            recipient_key=pix_key,
            recipient_name=self.merchant_name,
            transaction_id=transaction_id,
            description=description
        )
        
        # Generate QR code image
        qr_code_image = self.generate_qr_code_image(pix_code)
        
        return {
            'success': True,
            'transaction_id': transaction_id,
            'order_id': transaction_id,
            'amount': amount,
            'pix_code': pix_code,
            'qr_code_image': qr_code_image,
            'pix_key': pix_key,
            'recipient_name': self.merchant_name,
            'customer_name': customer_name,
            'customer_cpf': customer_cpf,
            'status': 'pending',
            'expires_at': (datetime.now() + timedelta(minutes=20)).isoformat(),
            'description': description
        }
    
    def generate_authentic_pix(self, amount: float, customer_name: str, customer_cpf: str, 
                              customer_email: str, description: str) -> dict:
        """
        Generate authentic Brazilian PIX using real PIX key from user
        """
        return self.create_pix_payment(amount, customer_name, customer_cpf, customer_email)

def create_brazilian_pix_provider():
    """Factory function to create Brazilian PIX provider"""
    return BrazilianPixGenerator()