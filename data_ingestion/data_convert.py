import csv

# Your CSV data as a string
data = """feedback_id,source,customer_name,product_name,feedback_text,rating,timestamp
1,website,John Doe,SmartPhone X,"The battery life is amazing, I love it!",5,2025-11-25 09:15:00
2,twitter,,SmartPhone X,"Terrible camera quality. Very disappointed.",1,2025-11-25 10:20:00
3,reddit,Alice,SmartWatch Pro,"Great features but the strap is uncomfortable.",3,2025-11-25 11:05:00
4,app_store,Bob,SmartWatch Pro,"Excellent app integration, very smooth.",5,2025-11-25 12:30:00
5,website,Charlie,SmartPhone X,"Screen cracked after a week. Poor build.",2,2025-11-25 13:45:00
6,twitter,,SmartHome Hub,"Setup was confusing, took too long.",2,2025-11-25 14:00:00
7,reddit,Diana,SmartHome Hub,"Works perfectly with Alexa and Google Home!",5,2025-11-25 15:10:00
8,app_store,Eric,SmartPhone X,"Average performance, could be faster.",3,2025-11-25 16:25:00
9,website,Fiona,SmartWatch Pro,"Battery lasts all week, very happy.",4,2025-11-25 17:40:00
10,twitter,,SmartHome Hub,"Customer service was helpful.",4,2025-11-25 18:55:00"""

# Split data into lines
lines = data.splitlines()

# Read CSV using csv.DictReader
reader = csv.DictReader(lines)

# Output CSV file
output_file = "feedback.csv"

with open(output_file, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=reader.fieldnames)
    writer.writeheader()
    for row in reader:
        writer.writerow(row)

print(f"CSV file '{output_file}' has been created successfully!")
