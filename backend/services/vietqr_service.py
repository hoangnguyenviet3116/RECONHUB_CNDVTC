from urllib.parse import quote
from decimal import Decimal

def generate_vietqr_url(bank_bin: str, account_no: str, amount: Decimal, order_code: str) -> str:
    memo = f"TT {order_code}"
    encoded_memo = quote(memo)
    amount_int = int(amount)
    return f"https://img.vietqr.io/image/{bank_bin}-{account_no}-compact2.png?amount={amount_int}&addInfo={encoded_memo}"