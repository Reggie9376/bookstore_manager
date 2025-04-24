import sqlite3
from typing import Optional

DB_NAME = "bookstore.db"

def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS member (
        mid TEXT PRIMARY KEY,
        mname TEXT NOT NULL,
        mphone TEXT NOT NULL,
        memail TEXT
    );

    CREATE TABLE IF NOT EXISTS book (
        bid TEXT PRIMARY KEY,
        btitle TEXT NOT NULL,
        bprice INTEGER NOT NULL,
        bstock INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS sale (
        sid INTEGER PRIMARY KEY AUTOINCREMENT,
        sdate TEXT NOT NULL,
        mid TEXT NOT NULL,
        bid TEXT NOT NULL,
        sqty INTEGER NOT NULL,
        sdiscount INTEGER NOT NULL,
        stotal INTEGER NOT NULL
    );

    INSERT OR IGNORE INTO member VALUES
        ('M001', 'Alice', '0912-345678', 'alice@example.com'),
        ('M002', 'Bob', '0923-456789', 'bob@example.com'),
        ('M003', 'Cathy', '0934-567890', 'cathy@example.com');

    INSERT OR IGNORE INTO book VALUES
        ('B001', 'Python Programming', 600, 50),
        ('B002', 'Data Science Basics', 800, 30),
        ('B003', 'Machine Learning Guide', 1200, 20);

    INSERT OR IGNORE INTO sale (sid, sdate, mid, bid, sqty, sdiscount, stotal) VALUES
        (1, '2024-01-15', 'M001', 'B001', 2, 100, 1100),
        (2, '2024-01-16', 'M002', 'B002', 1, 50, 750),
        (3, '2024-01-17', 'M001', 'B003', 3, 200, 3400),
        (4, '2024-01-18', 'M003', 'B001', 1, 0, 600);
    """)
    conn.commit()

def print_menu() -> None:
    print("""
***************選單***************
1. 新增銷售記錄
2. 顯示銷售報表
3. 更新銷售記錄
4. 刪除銷售記錄
5. 離開
**********************************
""")

def input_positive_int(prompt: str) -> int:
    while True:
        try:
            value = int(input(prompt))
            if value > 0:
                return value
            print("=> 錯誤：必須為正整數，請重新輸入")
        except ValueError:
            print("=> 錯誤：必須為正整數，請重新輸入")

def input_non_negative_int(prompt: str) -> int:
    while True:
        try:
            value = int(input(prompt))
            if value >= 0:
                return value
            print("=> 錯誤：折扣不能為負數，請重新輸入")
        except ValueError:
            print("=> 錯誤：折扣必須為整數，請重新輸入")

def add_sale(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()

    while True:
        sdate = input("請輸入銷售日期 (YYYY-MM-DD)：").strip()
        if len(sdate) == 10 and sdate.count('-') == 2:
            break
        print("=> 錯誤：日期格式不正確")

    while True:
        mid = input("請輸入會員編號：").strip()
        cursor.execute("SELECT * FROM member WHERE mid = ?", (mid,))
        if cursor.fetchone():
            break
        print("=> 錯誤：找不到會員編號，請重新輸入")

    while True:
        bid = input("請輸入書籍編號：").strip()
        cursor.execute("SELECT * FROM book WHERE bid = ?", (bid,))
        book = cursor.fetchone()
        if book:
            break
        print("=> 錯誤：找不到書籍編號，請重新輸入")

    sqty = input_positive_int("請輸入購買數量：")
    if sqty > book['bstock']:
        print(f"=> 錯誤：書籍庫存不足 (現有庫存: {book['bstock']})")
        return

    sdiscount = input_non_negative_int("請輸入折扣金額：")
    stotal = book['bprice'] * sqty - sdiscount

    try:
        cursor.execute("BEGIN")
        cursor.execute("""
            INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sdate, mid, bid, sqty, sdiscount, stotal))
        cursor.execute("UPDATE book SET bstock = bstock - ? WHERE bid = ?", (sqty, bid))
        conn.commit()
        print(f"=> 銷售記錄已新增！(銷售總額: {stotal:,})")
    except sqlite3.Error:
        conn.rollback()
        print("=> 錯誤：新增記錄時發生問題")

def print_sale_report(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sale.sid, sale.sdate, mname, btitle, bprice, sqty, sdiscount, stotal
        FROM sale
        JOIN member ON sale.mid = member.mid
        JOIN book ON sale.bid = book.bid
        ORDER BY sale.sid
    """)
    rows = cursor.fetchall()
    for i, row in enumerate(rows, 1):
        print(f"\n==================== 銷售報表 ====================")
        print(f"銷售 #{i}")
        print(f"銷售編號: {row['sid']}")
        print(f"銷售日期: {row['sdate']}")
        print(f"會員姓名: {row['mname']}")
        print(f"書籍標題: {row['btitle']}")
        print("--------------------------------------------------")
        print("單價\t數量\t折扣\t小計")
        print("--------------------------------------------------")
        print(f"{row['bprice']}\t{row['sqty']}\t{row['sdiscount']}\t{row['stotal']:,}")
        print("--------------------------------------------------")
        print(f"銷售總額: {row['stotal']:,}")
        print("==================================================")

def update_sale(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    sid = input("請輸入要更新的銷售編號：").strip()
    cursor.execute("SELECT * FROM sale WHERE sid = ?", (sid,))
    sale = cursor.fetchone()
    if not sale:
        print("=> 錯誤：找不到該銷售編號")
        return

    cursor.execute("SELECT * FROM book WHERE bid = ?", (sale['bid'],))
    book = cursor.fetchone()
    old_qty = sale['sqty']
    restock = old_qty

    new_qty = input_positive_int("請輸入新的購買數量：")
    if new_qty > book['bstock'] + restock:
        print(f"=> 錯誤：書籍庫存不足 (可用庫存: {book['bstock'] + restock})")
        return

    new_discount = input_non_negative_int("請輸入新的折扣金額：")
    new_total = book['bprice'] * new_qty - new_discount

    try:
        cursor.execute("BEGIN")
        cursor.execute("UPDATE sale SET sqty = ?, sdiscount = ?, stotal = ? WHERE sid = ?",
                       (new_qty, new_discount, new_total, sid))
        cursor.execute("UPDATE book SET bstock = bstock + ? - ? WHERE bid = ?",
                       (restock, new_qty, sale['bid']))
        conn.commit()
        print("=> 銷售記錄已更新！")
    except sqlite3.Error:
        conn.rollback()
        print("=> 錯誤：更新時發生問題")

def delete_sale(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    sid = input("請輸入要刪除的銷售編號：").strip()
    cursor.execute("SELECT * FROM sale WHERE sid = ?", (sid,))
    sale = cursor.fetchone()
    if not sale:
        print("=> 錯誤：找不到該銷售編號")
        return

    try:
        cursor.execute("BEGIN")
        cursor.execute("DELETE FROM sale WHERE sid = ?", (sid,))
        cursor.execute("UPDATE book SET bstock = bstock + ? WHERE bid = ?",
                       (sale['sqty'], sale['bid']))
        conn.commit()
        print("=> 銷售記錄已刪除！")
    except sqlite3.Error:
        conn.rollback()
        print("=> 錯誤：刪除時發生問題")

def main() -> None:
    with connect_db() as conn:
        initialize_db(conn)
        while True:
            print_menu()
            choice = input("請選擇操作項目(Enter 離開)：").strip()
            if choice == "":
                break
            elif choice == "1":
                add_sale(conn)
            elif choice == "2":
                print_sale_report(conn)
            elif choice == "3":
                update_sale(conn)
            elif choice == "4":
                delete_sale(conn)
            elif choice == "5":
                break
            else:
                print("=> 請輸入有效的選項（1-5）")

if __name__ == "__main__":
    main()
