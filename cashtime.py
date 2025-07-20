import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class CashtimeAPI:
    """
    API wrapper for Cashtime PIX payment integration
    """
    API_URL = "https://api.cashtime.com.br/v1"
    
    def __init__(self, secret_key: str, public_key: Optional[str] = None):
        self.secret_key = secret_key
        self.public_key = public_key
    
    def _get_headers(self) -> Dict[str, str]:
        """Create authentication headers for Cashtime API"""
        headers = {
            'Content-Type': 'application/json',
            'x-authorization-key': self.secret_key,
        }
        
        if self.public_key:
            headers['x-store-key'] = self.public_key
        
        return headers
    
    def _generate_txid(self) -> str:
        """Generate unique transaction ID"""
        return f"CASHTIME{int(datetime.now().timestamp())}{os.urandom(4).hex().upper()}"
    
    def _send_pushcut_notification(self, payment_data: Dict[str, Any], cashtime_result: Dict[str, Any]) -> None:
        """Send notification to Pushcut webhook when transaction is created"""
        try:
            pushcut_webhook_url = "https://api.pushcut.io/CwRJR0BYsyJYezzN-no_e/notifications/Sms"
            
            # Preparar dados da notificação
            customer_name = payment_data.get('name', 'Cliente')
            amount = payment_data.get('amount', 0)
            cashtime_id = cashtime_result.get('id', 'N/A')
            
            notification_payload = {
                "title": "🎉 Nova Venda PIX",
                "text": f"Cliente: {customer_name}\nValor: R$ {amount:.2f}\nID: {cashtime_id}",
                "isTimeSensitive": True
            }
            
            logger.info(f"Enviando notificação Pushcut: {notification_payload}")
            
            # Enviar notificação
            response = requests.post(
                pushcut_webhook_url,
                json=notification_payload,
                timeout=10
            )
            
            if response.ok:
                logger.info("Notificação Pushcut enviada com sucesso!")
            else:
                logger.warning(f"Falha ao enviar notificação Pushcut: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Erro ao enviar notificação Pushcut: {str(e)}")
    
    def create_pix_payment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a PIX payment request using Cashtime API"""
        try:
            logger.info("Iniciando criação de PIX via Cashtime...")
            
            # Validar dados obrigatórios
            required_fields = ['amount', 'description']
            for field in required_fields:
                if field not in data or not data[field]:
                    raise ValueError(f"Campo obrigatório ausente: {field}")
            
            # Gerar transaction ID único
            txid = self._generate_txid()
            expiration_minutes = data.get('expirationMinutes', 60)
            expires_at = datetime.now() + timedelta(minutes=expiration_minutes)
            
            # Converter valor para centavos
            amount_cents = int(float(data['amount']) * 100)
            
            # Clean and validate phone
            phone = data.get('phone', '11999999999')
            if not phone or phone == '':
                phone = '11999999999'
            # Remove any formatting from phone
            phone = ''.join(filter(str.isdigit, phone))
            if len(phone) < 10:
                phone = '11999999999'
            
            # Clean CPF
            cpf_clean = data.get('cpf', '').replace('.', '').replace('-', '')
            if not cpf_clean or len(cpf_clean) != 11:
                cpf_clean = '12345678901'  # Fallback CPF
            
            # Payload seguindo EXATAMENTE a documentação funcional
            cashtime_payload = {
                "paymentMethod": "pix",
                "customer": {
                    "name": data.get('name', 'Cliente'),
                    "email": data.get('email', 'email@dominio.com.br'),
                    "phone": phone,
                    "document": {
                        "number": cpf_clean,
                        "type": "cpf"
                    }
                },
                "items": [
                    {
                        "title": "Produto Digital PIX",
                        "description": data['description'],
                        "unitPrice": amount_cents,
                        "quantity": 1,
                        "tangible": False
                    }
                ],
                "isInfoProducts": True,
                "installments": 1,
                "installmentFee": 0,
                "postbackUrl": "https://webhook.site/unique-uuid-4-testing",
                "ip": "127.0.0.1",
                "amount": amount_cents
            }
            
            logger.info(f"Payload Cashtime: {json.dumps(cashtime_payload, indent=2)}")
            
            # Fazer requisição para API
            headers = self._get_headers()
            response = requests.post(
                f"{self.API_URL}/transactions",
                headers=headers,
                json=cashtime_payload,
                timeout=30
            )
            
            logger.info(f"Status da resposta Cashtime: {response.status_code}")
            
            if not response.ok:
                error_text = response.text
                logger.error(f"Erro na API Cashtime ({response.status_code}): {error_text}")
                logger.error(f"Headers enviados: {headers}")
                logger.error(f"Payload enviado: {json.dumps(cashtime_payload, indent=2)}")
                
                if response.status_code == 403:
                    raise Exception("Erro de autenticação. Verifique sua secret key da Cashtime")
                elif response.status_code == 400:
                    raise Exception(f"Dados inválidos enviados para a API: {error_text}")
                elif response.status_code == 500:
                    raise Exception(f"Erro interno da API Cashtime. Tente novamente em alguns minutos: {error_text}")
                else:
                    raise Exception(f"Erro na API Cashtime ({response.status_code}): {error_text}")
            
            cashtime_result = response.json()
            logger.info(f"Resposta Cashtime: {json.dumps(cashtime_result, indent=2)}")
            
            # Extrair dados do PIX
            pix_data = cashtime_result.get('pix', {})
            pix_code = pix_data.get('payload', '')
            qr_code_image = pix_data.get('encodedImage', '')
            
            # Formatar resposta padronizada
            result = {
                'success': True,
                'txid': txid,
                'cashtime_id': cashtime_result.get('id', ''),
                'amount': data['amount'],
                'currency': 'BRL',
                'description': data['description'],
                'status': cashtime_result.get('status', 'pending'),
                'pix_code': pix_code,
                'qr_code_image': qr_code_image,
                'expires_at': expires_at.isoformat(),
                'created_at': datetime.now().isoformat(),
                'payer': {
                    'name': data.get('name'),
                    'cpf': data.get('cpf'),
                    'email': data.get('email'),
                },
                'cashtime_response': cashtime_result
            }
            
            # Enviar notificação via Pushcut webhook
            self._send_pushcut_notification(data, cashtime_result)
            
            logger.info("PIX criado com sucesso via Cashtime!")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conexão com Cashtime: {str(e)}")
            raise Exception(f"Erro de conexão com a API: {str(e)}")
        except Exception as e:
            logger.error(f"Erro ao criar PIX: {str(e)}")
            raise Exception(f"Erro ao processar pagamento: {str(e)}")
    
    def check_payment_status(self, txid: str) -> Dict[str, Any]:
        """Check payment status by transaction ID"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f"{self.API_URL}/transactions/{txid}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 404:
                return {'success': False, 'error': 'Transação não encontrada'}
            
            if not response.ok:
                return {'success': False, 'error': f'Erro na API: {response.status_code}'}
            
            result = response.json()
            orders = result.get('orders', {})
            
            return {
                'success': True,
                'txid': txid,
                'status': orders.get('status', 'unknown'),
                'amount': orders.get('total', 0) / 100 if orders.get('total') else 0,
                'payment_method': orders.get('paymentMethod'),
                'created_at': orders.get('createdAt'),
                'updated_at': orders.get('updatedAt'),
                'cashtime_response': result
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar status: {str(e)}")
            return {'success': False, 'error': str(e)}


def create_cashtime_api(secret_key: Optional[str] = None, public_key: Optional[str] = None) -> CashtimeAPI:
    """Factory function to create CashtimeAPI instance"""
    if not secret_key:
        secret_key = os.environ.get('CASHTIME_SECRET_KEY')
        if not secret_key:
            raise ValueError("CASHTIME_SECRET_KEY não encontrada nas variáveis de ambiente")
    
    if not public_key:
        public_key = os.environ.get('CASHTIME_PUBLIC_KEY')
    
    return CashtimeAPI(secret_key=secret_key, public_key=public_key)