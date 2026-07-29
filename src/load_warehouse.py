import csv
from datetime import datetime

from warehouse.db import get_connection
from warehouse.models import (
    insert_city,
    get_city_id,
    insert_time,
    get_time_id,
    insert_facts_batch
)

CSV_FILE = "clean/air_quality_clean.csv"

def main():
    conn = get_connection()

    try:
        with open(CSV_FILE, encoding="utf-8") as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            print(f"{len(rows)} lignes trouvées")

            cities_done = set()
            for row in rows:
                ville_nom = row["ville"]
                if ville_nom not in cities_done:
                    city = {
                        "ville": ville_nom,
                        "pays": row["pays"],
                        "lat": float(row["latitude"]),
                        "lon": float(row["longitude"])
                    }
                    insert_city(city, conn)
                    cities_done.add(ville_nom)

            city_id_map = {}
            for row in rows:
                ville_nom = row["ville"]
                if ville_nom not in city_id_map:
                    city_id_map[ville_nom] = get_city_id(ville_nom, conn)

            times_done = set()
            for row in rows:
                timestamp_str = row["timestamp_utc"]
                if timestamp_str not in times_done:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
                    time_data = {
                        "timestamp": timestamp,
                        "date": row["date"],
                        "year": timestamp.year,
                        "month": timestamp.month,
                        "day": timestamp.day,
                        "hour": int(row["heure"]),
                        "day_of_week": row["jour_semaine"],
                        "is_weekend": row["is_weekend"] == "True"
                    }
                    insert_time(time_data, conn)
                    times_done.add(timestamp_str)

            time_id_map = {}
            for row in rows:
                timestamp_str = row["timestamp_utc"]
                if timestamp_str not in time_id_map:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
                    time_id_map[timestamp_str] = get_time_id(timestamp, conn)

            facts = []
            for row in rows:
                city_id = city_id_map[row["ville"]]
                time_id = time_id_map[row["timestamp_utc"]]
                facts.append((
                    city_id,
                    time_id,
                    int(row["aqi"]),
                    float(row["co"]) if row["co"] != "" else None,
                    float(row["no"]) if row["no"] != "" else None,
                    float(row["no2"]) if row["no2"] != "" else None,
                    float(row["o3"]) if row["o3"] != "" else None,
                    float(row["so2"]) if row["so2"] != "" else None,
                    float(row["pm2_5"]) if row["pm2_5"] != "" else None,
                    float(row["pm10"]) if row["pm10"] != "" else None,
                    float(row["nh3"]) if row["nh3"] != "" else None
                ))

            insert_facts_batch(facts, conn)
            print(f"✅ {len(facts)} faits insérés dans le data warehouse.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()