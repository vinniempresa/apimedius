import os
import requests
from datetime import datetime
from flask import current_app, request
from typing import Dict, Any, Optional
import random
import string
import time

class For4PaymentsAPI:
    API_URL = "https://app.for4payments.com.br/api/v1"

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.extra_headers = {}  # Headers adicionais para evitar problemas de 403 Forbidden

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            'Authorization': self.secret_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        # Adicionar headers extras (para evitar 403 Forbidden)
        if self.extra_headers:
            headers.update(self.extra_headers)
            current_app.logger.debug(f"Usando headers personalizados: {headers}")

        return headers

    def _generate_random_email(self, name: str) -> str:
        clean_name = ''.join(e.lower() for e in name if e.isalnum())
        random_num = ''.join(random.choices(string.digits, k=4))
        domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
        domain = random.choice(domains)
        return f"{clean_name}{random_num}@{domain}"

    def _generate_random_phone(self) -> str:
        """
        Gera um número de telefone brasileiro aleatório no formato DDDNNNNNNNNN
        sem o prefixo +55. Usado apenas como fallback quando um telefone válido não está disponível.
        """
        ddd = str(random.randint(11, 99))
        number = ''.join(random.choices(string.digits, k=9))
        return f"{ddd}{number}"

    def create_pix_payment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a PIX payment request"""
        # Registro detalhado da chave secreta (parcial)
        if not self.secret_key:
            current_app.logger.error("Token de autenticação não fornecido")
            raise ValueError("Token de autenticação não foi configurado")
        elif len(self.secret_key) < 10:
            current_app.logger.error(f"Token de autenticação muito curto ({len(self.secret_key)} caracteres)")
            raise ValueError("Token de autenticação inválido (muito curto)")
        else:
            current_app.logger.info(f"Utilizando token de autenticação: {self.secret_key[:3]}...{self.secret_key[-3:]} ({len(self.secret_key)} caracteres)")

        # Log dos dados recebidos para processamento
        safe_data = {k: v for k, v in data.items()}
        if 'cpf' in safe_data:
            safe_data['cpf'] = f"{safe_data['cpf'][:3]}...{safe_data['cpf'][-2:]}" if len(safe_data['cpf']) > 5 else "***"
        current_app.logger.info(f"Dados recebidos para pagamento: {safe_data}")

        # Validação dos campos obrigatórios
        required_fields = ['name', 'email', 'cpf', 'amount']
        missing_fields = []
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append(field)

        if missing_fields:
            current_app.logger.error(f"Campos obrigatórios ausentes: {missing_fields}")
            raise ValueError(f"Campos obrigatórios ausentes: {', '.join(missing_fields)}")

        try:
            # Validação e conversão do valor
            try:
                amount_in_cents = int(float(data['amount']) * 100)
                current_app.logger.info(f"Valor do pagamento: R$ {float(data['amount']):.2f} ({amount_in_cents} centavos)")
            except (ValueError, TypeError) as e:
                current_app.logger.error(f"Erro ao converter valor do pagamento: {str(e)}")
                raise ValueError(f"Valor de pagamento inválido: {data['amount']}")

            if amount_in_cents <= 0:
                current_app.logger.error(f"Valor do pagamento não positivo: {amount_in_cents}")
                raise ValueError("Valor do pagamento deve ser maior que zero")

            # Processamento do CPF
            cpf = ''.join(filter(str.isdigit, str(data['cpf'])))
            if len(cpf) != 11:
                current_app.logger.error(f"CPF com formato inválido: {cpf} (comprimento: {len(cpf)})")
                raise ValueError("CPF inválido - deve conter 11 dígitos")
            else:
                current_app.logger.info(f"CPF validado: {cpf[:3]}...{cpf[-2:]}")

            # Validação de email - prioriza o email fornecido
            email = data.get('email')
            if not email or '@' not in email:
                current_app.logger.warning(f"Email não fornecido ou inválido: {email}")
                # Só gera email aleatório como último recurso
                email = self._generate_random_email(data['name'])
                current_app.logger.info(f"Email gerado como fallback: {email}")
            else:
                current_app.logger.info(f"Email válido fornecido: {email}")

            # Processamento do telefone
            phone = data.get('phone', '')

            # Verifica se o telefone foi fornecido e processa
            if phone and isinstance(phone, str) and len(phone.strip()) > 0:
                # Remove caracteres não numéricos
                phone = ''.join(filter(str.isdigit, phone))

                # Verifica se o número tem um formato aceitável após a limpeza
                if len(phone) >= 10:
                    # Se existir o prefixo brasileiro 55, garante que ele seja removido para o padrão da API
                    if phone.startswith('55') and len(phone) > 10:
                        phone = phone[2:]
                    current_app.logger.info(f"Telefone do usuário processado: {phone}")
                else:
                    current_app.logger.warning(f"Telefone fornecido inválido (muito curto): {phone}")
                    phone = self._generate_random_phone()
                    current_app.logger.info(f"Telefone gerado automaticamente como fallback: {phone}")
            else:
                # Se não houver telefone ou for inválido, gerar um aleatório
                phone = self._generate_random_phone()
                current_app.logger.info(f"Telefone não fornecido, gerado automaticamente: {phone}")

            # Preparação dos dados para a API
            payment_data = {
                "name": data['name'],
                "email": email,
                "cpf": cpf,
                "phone": phone,
                "paymentMethod": "PIX",
                "amount": amount_in_cents,
                "items": [{
                    "title": "Regularizar Débitos",
                    "quantity": 1,
                    "unitPrice": amount_in_cents,
                    "tangible": False
                }]
            }

            current_app.logger.info(f"Dados de pagamento formatados: {payment_data}")
            current_app.logger.info(f"Endpoint API: {self.API_URL}/transaction.purchase")
            current_app.logger.info("Enviando requisição para API For4Payments...")

            try:
                # Gerar headers aleatórios para evitar bloqueios
                user_agents = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
                    "Mozilla/5.0 (Android 12; Mobile; rv:68.0) Gecko/68.0 Firefox/94.0",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0"
                ]

                languages = [
                    "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                    "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
                    "es-ES,es;q=0.9,pt;q=0.8,en;q=0.7"
                ]

                # Configurar headers extras aleatórios
                extra_headers = {
                    "User-Agent": random.choice(user_agents),
                    "Accept-Language": random.choice(languages),
                    "Cache-Control": random.choice(["max-age=0", "no-cache"]),
                    "X-Requested-With": "XMLHttpRequest",
                    "X-Cache-Buster": str(int(time.time() * 1000)),
                    "Referer": "https://encceja2025.com.br/pagamento",
                    "Sec-Fetch-Site": "same-origin",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Dest": "empty"
                }

                # Combinar com headers base
                headers = self._get_headers()
                headers.update(extra_headers)

                current_app.logger.info(f"Usando headers aleatórios para For4Payments API")

                response = requests.post(
                    f"{self.API_URL}/transaction.purchase",
                    json=payment_data,
                    headers=headers,
                    timeout=30
                )

                current_app.logger.info(f"Resposta recebida (Status: {response.status_code})")
                current_app.logger.debug(f"Resposta completa: {response.text}")

                if response.status_code == 200:
                    response_data = response.json()
                    current_app.logger.info(f"Resposta da API: {response_data}")

                    # Log detalhado para identificar todos os campos relevantes
                    pixcode_fields = []
                    qrcode_fields = []

                    # Verificar campos principais no primeiro nível
                    for field in ['pixCode', 'copy_paste', 'code', 'pix_code']:
                        if field in response_data:
                            pixcode_fields.append(f"{field}: {str(response_data.get(field))[:30]}...")

                    for field in ['pixQrCode', 'qr_code_image', 'qr_code', 'pix_qr_code']:
                        if field in response_data:
                            qrcode_fields.append(f"{field}: presente")

                    # Verificar em estruturas aninhadas (pix)
                    if 'pix' in response_data and isinstance(response_data.get('pix'), dict):
                        pix_data = response_data.get('pix', {})
                        for field in ['code', 'copy_paste', 'pixCode']:
                            if field in pix_data:
                                pixcode_fields.append(f"pix.{field}: {str(pix_data.get(field))[:30]}...")

                        for field in ['qrCode', 'qr_code_image', 'pixQrCode']:
                            if field in pix_data:
                                qrcode_fields.append(f"pix.{field}: presente")

                    # Log dos campos encontrados
                    current_app.logger.info(f"Campos de código PIX encontrados: {pixcode_fields}")
                    current_app.logger.info(f"Campos de QR code encontrados: {qrcode_fields}")

                    # Resultado formatado com suporte a múltiplos formatos de resposta
                    result = {
                        'id': response_data.get('id') or response_data.get('transactionId'),
                        'pixCode': (
                            response_data.get('pixCode') or 
                            response_data.get('copy_paste') or 
                            response_data.get('code') or 
                            response_data.get('pix_code') or
                            (response_data.get('pix', {}) or {}).get('code') or 
                            (response_data.get('pix', {}) or {}).get('copy_paste')
                        ),
                        'pixQrCode': (
                            response_data.get('pixQrCode') or 
                            response_data.get('qr_code_image') or 
                            response_data.get('qr_code') or 
                            response_data.get('pix_qr_code') or
                            (response_data.get('pix', {}) or {}).get('qrCode') or 
                            (response_data.get('pix', {}) or {}).get('qr_code_image')
                        ),
                        'expiresAt': response_data.get('expiresAt') or response_data.get('expiration'),
                        'status': response_data.get('status', 'pending')
                    }

                    current_app.logger.info(f"Resultado final formatado: {result}")

                    if not result['pixCode'] and not result['pixQrCode']:
                        current_app.logger.error("Nenhum código PIX ou QR code encontrado na resposta")
                        raise ValueError("Resposta da API não contém dados de pagamento PIX válidos")

                    return result

                elif response.status_code == 401:
                    current_app.logger.error("Erro de autenticação com a API For4Payments")
                    raise ValueError("Falha na autenticação com a API For4Payments. Verifique a chave de API.")
                elif response.status_code == 403:
                    current_app.logger.error("Acesso negado pela API For4Payments")
                    raise ValueError("Acesso negado pela API For4Payments. Verifique as permissões da chave de API.")
                else:
                    error_message = 'Erro ao processar pagamento'
                    try:
                        error_data = response.json()
                        if isinstance(error_data, dict):
                            error_message = error_data.get('message') or error_data.get('error') or '; '.join(error_data.get('errors', []))
                            current_app.logger.error(f"Erro da API For4Payments: {error_message}")
                    except Exception as e:
                        error_message = f'Erro ao processar pagamento (Status: {response.status_code})'
                        current_app.logger.error(f"Erro ao processar resposta da API: {str(e)}")
                    raise ValueError(error_message)

            except requests.exceptions.RequestException as e:
                current_app.logger.error(f"Erro de conexão com a API For4Payments: {str(e)}")
                raise ValueError("Erro de conexão com o serviço de pagamento. Tente novamente em alguns instantes.")

        except ValueError as e:
            current_app.logger.error(f"Erro de validação: {str(e)}")
            raise
        except Exception as e:
            current_app.logger.error(f"Erro inesperado ao processar pagamento: {str(e)}")
            raise ValueError("Erro interno ao processar pagamento. Por favor, tente novamente.")

def create_payment_api(secret_key: Optional[str] = None) -> For4PaymentsAPI:
    """Factory function to create For4PaymentsAPI instance"""
    if secret_key is None:
        secret_key = os.environ.get("FOR4PAYMENTS_SECRET_KEY")
        if not secret_key:
            raise ValueError("FOR4PAYMENTS_SECRET_KEY não configurada")
    return For4PaymentsAPI(secret_key)