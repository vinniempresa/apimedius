import os
import requests
import base64
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MediusPagAPI:
    """
    API wrapper for MEDIUS PAG payment integration
    """
    API_URL = "https://api.mediuspag.com/functions/v1"
    
    def __init__(self, secret_key: str, company_id: str = "2a3d291b-47fc-4c60-9046-d68700283585"):
        self.secret_key = secret_key
        self.company_id = company_id
    
    def _get_headers(self) -> Dict[str, str]:
        """Create authentication headers for MEDIUS PAG API"""
        # Create basic auth header as per documentation
        auth_string = f"{self.secret_key}:x"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        return {
            'Authorization': f'Basic {encoded_auth}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID"""
        timestamp = int(datetime.now().timestamp())
        unique_id = str(uuid.uuid4()).replace('-', '')[:8]
        return f"MP{timestamp}{unique_id}"
    
    def create_pix_transaction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a PIX transaction using MEDIUS PAG API"""
        try:
            logger.info("Iniciando criação de transação PIX via MEDIUS PAG...")
            
            # Validar dados obrigatórios
            required_fields = ['amount', 'customer_name', 'customer_cpf']
            missing_fields = []
            for field in required_fields:
                if field not in data or not data[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                raise ValueError(f"Campos obrigatórios ausentes: {', '.join(missing_fields)}")
            
            # Preparar dados da transação
            transaction_id = self._generate_transaction_id()
            
            # Dados padrão fornecidos pelo usuário
            default_email = "gerarpagamento@gmail.com"
            default_phone = "(11) 98768-9080"
            
            # Testando diferentes estruturas de payload para MEDIUS PAG
            amount_in_cents = int(data['amount'] * 100)  # Converter para centavos
            
            # MEDIUS PAG payload corrigido com campos obrigatórios
            amount_cents = int(data['amount'] * 100)
            
            # Payload completo baseado no padrão MEDIUS PAG/owempay.com.br
            payload = {
                "amount": amount_cents,
                "description": "Receita de bolo",
                "paymentMethod": "PIX",
                "customer": {
                    "name": data.get('customer_name', 'Cliente'),
                    "email": data.get('customer_email', default_email),
                    "phone": data.get('customer_phone', default_phone),
                    "cpf": data.get('customer_cpf', '').replace('.', '').replace('-', '') if data.get('customer_cpf') else None
                },
                "companyId": "30427d55-e437-4384-88de-6ba84fc74833",
                "externalId": transaction_id,
                "products": [
                    {
                        "name": "Receita de bolo",
                        "quantity": 1,
                        "price": amount_cents
                    }
                ]
            }
            
            # Remover campos None para evitar erros
            if payload["customer"]["cpf"] is None:
                del payload["customer"]["cpf"]
            
            logger.info(f"Enviando transação PIX: {transaction_id}")
            logger.info(f"Valor: R$ {data['amount']:.2f}")
            
            # Fazer requisição para API
            headers = self._get_headers()
            response = requests.post(
                f"{self.API_URL}/transactions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            logger.info(f"Status da resposta MEDIUS PAG: {response.status_code}")
            
            if response.status_code in [200, 201]:
                try:
                    result = response.json()
                    logger.info(f"Resposta MEDIUS PAG: {json.dumps(result, indent=2)}")
                    
                    # Extrair dados importantes da resposta MEDIUS PAG
                    pix_data = {
                        'success': True,
                        'transaction_id': result.get('id', transaction_id),
                        'order_id': result.get('id', transaction_id),
                        'amount': data['amount'],
                        'status': result.get('status', 'pending'),
                        'created_at': result.get('createdAt', datetime.now().isoformat())
                    }
                    
                    # Buscar PIX code na estrutura de resposta da MEDIUS PAG
                    pix_code_found = False
                    qr_code_found = False
                    
                    # Buscar PIX code na estrutura aninhada da MEDIUS PAG
                    # Baseado nos logs: result["pix"]["qrcode"] é o campo correto
                    if 'pix' in result and isinstance(result['pix'], dict):
                        pix_info = result['pix']
                        
                        # Campo correto da MEDIUS PAG é "qrcode"
                        if 'qrcode' in pix_info and pix_info['qrcode']:
                            pix_data['pix_code'] = pix_info['qrcode']
                            pix_code_found = True
                            logger.info(f"✅ PIX code real MEDIUS PAG encontrado: {pix_info['qrcode'][:50]}...")
                        
                        # Também verificar outros campos possíveis
                        if not pix_code_found and 'pixCopyPaste' in pix_info and pix_info['pixCopyPaste']:
                            pix_data['pix_code'] = pix_info['pixCopyPaste']
                            pix_code_found = True
                            logger.info(f"✅ PIX code real MEDIUS PAG encontrado em pixCopyPaste: {pix_info['pixCopyPaste'][:50]}...")
                        
                        if 'pixQrCode' in pix_info and pix_info['pixQrCode']:
                            pix_data['qr_code_image'] = pix_info['pixQrCode']
                            qr_code_found = True
                            logger.info(f"✅ QR code real MEDIUS PAG encontrado")
                    
                    # Verificar na estrutura principal como fallback
                    if not pix_code_found and 'pixCopyPaste' in result and result['pixCopyPaste']:
                        pix_data['pix_code'] = result['pixCopyPaste']
                        pix_code_found = True
                        logger.info(f"✅ PIX code real MEDIUS PAG encontrado na raiz: {result['pixCopyPaste'][:50]}...")
                    
                    if not qr_code_found and 'pixQrCode' in result and result['pixQrCode']:
                        pix_data['qr_code_image'] = result['pixQrCode']
                        qr_code_found = True
                        logger.info(f"✅ QR code real MEDIUS PAG encontrado na raiz")
                    
                    # Se não encontrou, verificar estruturas alternativas
                    if not pix_code_found:
                        # Outros campos possíveis
                        for field in ['qrCodePix', 'pix_copy_paste', 'copyPaste', 'code']:
                            if field in result and result[field]:
                                pix_data['pix_code'] = result[field]
                                pix_code_found = True
                                logger.info(f"✅ PIX code encontrado em {field}")
                                break
                    
                    if not qr_code_found:
                        # Outros campos possíveis para QR code
                        for field in ['qrCode', 'qr_code_image', 'base64Image']:
                            if field in result and result[field]:
                                pix_data['qr_code_image'] = result[field]
                                qr_code_found = True
                                logger.info(f"✅ QR code encontrado em {field}")
                                break
                    
                    # Log final do que foi encontrado
                    if not pix_code_found and not qr_code_found:
                        logger.warning("Resposta MEDIUS PAG não contém dados PIX válidos")
                    else:
                        logger.info(f"✅ MEDIUS PAG - PIX: {pix_code_found}, QR: {qr_code_found}")
                    
                    # Definir valores padrão vazios se não encontrados
                    if not pix_code_found:
                        pix_data['pix_code'] = ''
                    if not qr_code_found:
                        pix_data['qr_code_image'] = ''
                    
                    # Enviar notificação Pushcut se PIX foi criado com sucesso
                    if pix_code_found:
                        self._send_pushcut_notification(data, pix_data)
                    
                    return pix_data
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Erro ao decodificar resposta JSON: {e}")
                    logger.error(f"Resposta bruta: {response.text}")
                    raise Exception(f"Erro ao processar resposta da API: {e}")
            else:
                error_msg = f"Erro na API MEDIUS PAG - Status: {response.status_code}"
                logger.error(error_msg)
                logger.error(f"Resposta: {response.text}")
                
                # Tentar extrair mensagem de erro da resposta
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg = f"Erro MEDIUS PAG: {error_data['message']}"
                    elif 'error' in error_data:
                        error_msg = f"Erro MEDIUS PAG: {error_data['error']}"
                except:
                    pass
                
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conectividade com MEDIUS PAG: {e}")
            raise Exception(f"Erro de conectividade: {str(e)}")
        except Exception as e:
            logger.error(f"Erro ao criar transação PIX: {e}")
            raise Exception(f"Erro ao processar pagamento: {str(e)}")
    
    def get_transaction_by_id(self, transaction_id: str) -> Dict[str, Any]:
        """Get transaction details by ID from MEDIUS PAG"""
        try:
            logger.info(f"Buscando transação MEDIUS PAG: {transaction_id}")
            
            headers = self._get_headers()
            response = requests.get(
                f"{self.API_URL}/transactions/{transaction_id}",
                headers=headers,
                timeout=15
            )
            
            logger.info(f"Status da busca MEDIUS PAG: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Transação encontrada: {json.dumps(result, indent=2)}")
                
                # Extrair PIX real da transação MEDIUS PAG
                pix_data = {
                    'success': True,
                    'transaction_id': result.get('id', transaction_id),
                    'order_id': result.get('id', transaction_id),
                    'amount': result.get('amount', 0) / 100,  # Converter de centavos
                    'pix_code': result.get('pixCopyPaste', result.get('pix_copy_paste', result.get('qrCodePix', ''))),
                    'qr_code_image': result.get('pixQrCode', result.get('qr_code_image', result.get('qrCode', ''))),
                    'status': result.get('status', 'pending'),
                    'created_at': result.get('createdAt', ''),
                    'description': result.get('description', 'Receita de bolo')
                }
                
                return pix_data
            else:
                logger.error(f"Erro ao buscar transação: {response.status_code} - {response.text}")
                return {'success': False, 'error': f'Transação não encontrada: {transaction_id}'}
                
        except Exception as e:
            logger.error(f"Erro ao buscar transação: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        """Check the status of a PIX transaction"""
        try:
            logger.info(f"Verificando status da transação: {transaction_id}")
            
            headers = self._get_headers()
            response = requests.get(
                f"{self.API_URL}/transactions/{transaction_id}",
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'status': data.get('status', 'unknown'),
                    'transaction_id': transaction_id,
                    'amount': data.get('amount'),
                    'paid_at': data.get('paid_at'),
                    'data': data
                }
            else:
                logger.error(f"Erro ao verificar status - Status: {response.status_code}")
                return {
                    'success': False,
                    'error': f"Erro ao verificar status: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Erro ao verificar status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_pushcut_notification(self, payment_data: Dict[str, Any], pix_result: Dict[str, Any]) -> None:
        """Send notification to Pushcut webhook when PIX transaction is created"""
        try:
            pushcut_webhook_url = "https://api.pushcut.io/NiUWvkdg8_MMjxh6DOpez/notifications/Venda%20Pendente"
            
            # Preparar dados da notificação
            customer_name = payment_data.get('customer_name', 'Cliente')
            amount = payment_data.get('amount', 0)
            transaction_id = pix_result.get('transaction_id', 'N/A')
            
            notification_payload = {
                "title": "🎉 Nova Venda PIX",
                "text": f"Cliente: {customer_name}\nValor: R$ {amount:.2f}\nID: {transaction_id}",
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
                logger.info("✅ Notificação Pushcut enviada com sucesso!")
            else:
                logger.warning(f"❌ Falha ao enviar notificação Pushcut: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"❌ Erro ao enviar notificação Pushcut: {str(e)}")

def create_medius_pag_api(secret_key: Optional[str] = None, company_id: Optional[str] = None) -> MediusPagAPI:
    """Factory function to create MediusPagAPI instance"""
    if not secret_key:
        secret_key = os.environ.get('MEDIUS_PAG_SECRET_KEY')
        if not secret_key:
            raise ValueError("MEDIUS_PAG_SECRET_KEY não encontrada nas variáveis de ambiente")
    
    if not company_id:
        company_id = os.environ.get('MEDIUS_PAG_COMPANY_ID', '30427d55-e437-4384-88de-6ba84fc74833')
    
    # Ensure company_id is not None
    final_company_id = company_id or '30427d55-e437-4384-88de-6ba84fc74833'
    
    return MediusPagAPI(secret_key=secret_key, company_id=final_company_id)