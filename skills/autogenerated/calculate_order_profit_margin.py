from typing import Any
from skills.base_skill import BaseSkill

class CalculateOrderProfitMargin(BaseSkill):
    name = "calculate_order_profit_margin"
    description = "Calculate profit margin for a sales order by comparing unit price to standard cost"
    domain = "sales"

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        from agent.db import get_connection
        
        order_id = kwargs.get("order_id")
        if not order_id:
            return {"success": False, "error": "order_id parameter is required"}
        
        try:
            async with await get_connection() as conn:
                rows = await (await conn.execute(
                    """
                    SELECT 
                        sod.salesorderid,
                        sod.productid,
                        p.name as product_name,
                        sod.orderqty,
                        sod.unitprice,
                        p.standardcost,
                        sod.linetotal,
                        (sod.orderqty * p.standardcost) as total_cost,
                        (sod.linetotal - (sod.orderqty * p.standardcost)) as profit,
                        CASE 
                            WHEN sod.linetotal > 0 
                            THEN ROUND(((sod.linetotal - (sod.orderqty * p.standardcost)) / sod.linetotal * 100), 2)
                            ELSE 0 
                        END as margin_percentage
                    FROM sales.salesorderdetail sod
                    INNER JOIN production.product p ON sod.productid = p.productid
                    WHERE sod.salesorderid = %(order_id)s
                    ORDER BY sod.salesorderdetailid
                    """,
                    {"order_id": order_id}
                )).fetchall()
                
                if not rows:
                    return {"success": False, "error": f"Sales order {order_id} not found"}
                
                # Calculate overall order totals
                total_revenue = sum(row[6] for row in rows)  # linetotal
                total_cost = sum(row[7] for row in rows)     # total_cost
                total_profit = total_revenue - total_cost
                overall_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
                
                # Format response
                line_items = []
                for row in rows:
                    line_items.append({
                        "product_id": row[1],
                        "product_name": row[2],
                        "quantity": row[3],
                        "unit_price": float(row[4]),
                        "standard_cost": float(row[5]),
                        "line_total": float(row[6]),
                        "total_cost": float(row[7]),
                        "profit": float(row[8]),
                        "margin_percentage": float(row[9])
                    })
                
                return {
                    "success": True,
                    "data": {
                        "order_id": order_id,
                        "total_revenue": round(total_revenue, 2),
                        "total_cost": round(total_cost, 2),
                        "total_profit": round(total_profit, 2),
                        "overall_margin_percentage": round(overall_margin, 2),
                        "line_items": line_items
                    }
                }
                
        except Exception as e:
            return {"success": False, "error": f"Database error: {str(e)}"}