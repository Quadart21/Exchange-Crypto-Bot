# webhook_server.py
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from heleket_api import verify_webhook

app = FastAPI()

@app.post("/callback")
async def heleket_callback(request: Request):
    data = await request.json()
    if not verify_webhook(data):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    status = data.get('status')
    order_id = data.get('order_id')
    
    if status in ("paid", "paid_over"):
        # Комментарий: здесь добавить обработку успешного платежа
        print(f"Платёж зачислен! Order ID: {order_id}, Сумма: {data.get('payment_amount')} {data.get('currency')}")
    
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
