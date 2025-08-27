# -*- coding: utf-8 -*-
# pip install mysql-connector-python
import mysql.connector as mc

TABLE = "drama"

SRC = dict(host="192.168.14.38", port=3310, user="lguplus7",
           password="lg7p@ssw0rd~!", database="cp_data", charset="utf8mb4")
DST = dict(host="127.0.0.1",     port=3310, user="lguplus7",
           password="lg7p@ssw0rd~!", database="cp_data", charset="utf8mb4")

BATCH = 2000

def connect(cfg):
    conn = mc.connect(**cfg, autocommit=False)
    # charset으로 이미 세션 인코딩 설정됨. 필요시 아래 한 줄 추가로 고정 가능:
    # conn.cursor().execute("SET NAMES utf8mb4")
    return conn

src = connect(SRC); dst = connect(DST)
s = src.cursor();   d = dst.cursor()

# 스키마가 완전히 같다는 전제: SELECT * → REPLACE INTO VALUES(...)
s.execute(f"SELECT * FROM `{TABLE}`")
cols = len(s.column_names)
place = ",".join(["%s"] * cols)

sql = f"REPLACE INTO `{TABLE}` VALUES ({place})"  # PK/UNIQUE 충돌 시 덮어쓰기
buf, moved = [], 0

for row in s:
    buf.append(row)
    if len(buf) >= BATCH:
        d.executemany(sql, buf)
        dst.commit()
        moved += len(buf); buf.clear()
        print("moved:", moved)

if buf:
    d.executemany(sql, buf)
    dst.commit()
    moved += len(buf)

print("done, total:", moved)
s.close(); d.close()
src.close(); dst.close()
