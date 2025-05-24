from fastapi import APIRouter, Request, HTTPException 
from heleket_api import verify_webhook
from database.db import create_connection
from config import bot

router = APIRouter()

@router.post("/webhook")
async def heleket_webhook(request: Request):
    data = await request.json()

    if not verify_webhook(data):
        raise HTTPException(status_code=403, detail="Invalid signature")

    order_id = data.get("order_id")
    status = data.get("status")
    txid = data.get("txid")

    if not order_id:
        raise HTTPException(status_code=400, detail="No order_id")

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM orders WHERE uuid = ?", (data["uuid"],))
    row = cursor.fetchone()

    if row:
        user_id = row[0]
        cursor.execute("""
            UPDATE orders SET status = ?, details = ?
            WHERE uuid = ?
        """, (status, txid or "", data["uuid"]))
        conn.commit()

        # уведомляем, если отмена
        if status == "cancel":
            await bot.send_message(
                user_id,
                "❌ Ваша заявка была отменена, так как по ней не поступила оплата."
            )

    conn.close()
    return {"status": "ok"}
