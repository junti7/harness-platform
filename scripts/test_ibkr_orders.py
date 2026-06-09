import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ib_insync import IB
import logging
logging.basicConfig(level=logging.INFO)

def main():
    ib = IB()
    try:
        ib.connect("127.0.0.1", 4002, clientId=99)
        print("Connected!")
        
        print("\n--- reqAllOpenOrders ---")
        open_orders = ib.reqAllOpenOrders()
        print(f"Count: {len(open_orders)}")
        for o in open_orders:
            print(f"Symbol: {o.contract.symbol}, Action: {o.order.action}, Status: {o.orderStatus.status if o.orderStatus else 'None'}, Qty: {o.order.totalQuantity}")
            
        print("\n--- reqExecutions ---")
        executions = ib.reqExecutions()
        print(f"Count: {len(executions)}")
        for e in executions:
            print(e)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ib.disconnect()

if __name__ == "__main__":
    main()
