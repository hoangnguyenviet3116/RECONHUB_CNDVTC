# -*- coding: utf-8 -*-
import sys
import pyodbc

sys.stdout.reconfigure(encoding='utf-8')

conn = pyodbc.connect('Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=VietQR_ReconHub;Trusted_Connection=yes;', autocommit=True)
cursor = conn.cursor()

sql = """
IF NOT EXISTS (
    SELECT 1 FROM sys.columns 
    WHERE object_id = OBJECT_ID('dbo.shifts') AND name = 'closed_at'
)
BEGIN
    ALTER TABLE dbo.shifts ADD closed_at DATETIME2 NULL;
    PRINT 'Added closed_at column to dbo.shifts';
END
ELSE
BEGIN
    PRINT 'Column closed_at already exists in dbo.shifts';
END
"""

cursor.execute(sql)
print("Migration completed successfully.")
