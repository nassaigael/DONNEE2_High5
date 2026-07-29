from warehouse.db import get_connection
from psycopg2.extras import execute_values


def insert_city(city, conn=None):
    """
    Insère une ville si elle n'existe pas déjà.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO dim_city (city_name, country, latitude, longitude)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (city_name) DO NOTHING;
            """, (
                city["ville"],
                city["pays"],
                city["lat"],
                city["lon"]
            ))
            conn.commit()
    finally:
        if close_conn:
            conn.close()


def get_city_id(city_name, conn=None):
    """
    Récupère le city_id correspondant au nom de la ville.
    Renvoie None si introuvable.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT city_id
                FROM dim_city
                WHERE city_name = %s;
            """, (city_name,))
            result = cur.fetchone()
            return result[0] if result else None
    finally:
        if close_conn:
            conn.close()


def insert_time(time_data, conn=None):
    """
    Insère un timestamp dans dim_time et retourne systématiquement le time_id.
    Utilise un UPSERT factice pour garantir un retour direct sans faire 2 requêtes.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO dim_time (
                    timestamp_hour, date_value, year, month, day, hour, day_of_week, is_weekend
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (timestamp_hour) 
                DO UPDATE SET timestamp_hour = EXCLUDED.timestamp_hour
                RETURNING time_id;
            """, (
                time_data["timestamp"],
                time_data["date"],
                time_data["year"],
                time_data["month"],
                time_data["day"],
                time_data["hour"],
                time_data["day_of_week"],
                time_data["is_weekend"]
            ))
            time_id = cur.fetchone()[0]
            conn.commit()
            return time_id
    finally:
        if close_conn:
            conn.close()


def get_time_id(timestamp, conn=None):
    """
    Récupère le time_id via le timestamp.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT time_id FROM dim_time WHERE timestamp_hour = %s;", 
                (timestamp,)
            )
            result = cur.fetchone()
            if result:
                return result[0]
            raise ValueError(f"Timestamp {timestamp} non trouvé dans dim_time")
    finally:
        if close_conn:
            conn.close()


def insert_fact(fact, conn=None):
    """
    Insère une mesure individuelle dans la table de faits.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO fact_air_quality (
                    city_id, time_id, aqi, co, no, no2, o3, so2, pm2_5, pm10, nh3
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (city_id, time_id) DO NOTHING;
            """, (
                fact["city_id"],
                fact["time_id"],
                fact["aqi"],
                fact["co"],
                fact["no"],
                fact["no2"],
                fact["o3"],
                fact["so2"],
                fact["pm2_5"],
                fact["pm10"],
                fact["nh3"]
            ))
            conn.commit()
    finally:
        if close_conn:
            conn.close()


def insert_facts_batch(facts, conn=None):
    """
    Insère un lot de mesures (recommandé pour les performances).
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO fact_air_quality (
                    city_id, time_id, aqi, co, no, no2, o3, so2, pm2_5, pm10, nh3
                )
                VALUES %s
                ON CONFLICT (city_id, time_id) DO NOTHING;
            """
            execute_values(cur, sql, facts, page_size=1000)
            conn.commit()
    finally:
        if close_conn:
            conn.close()
