import os
import json

import pymysql

from flask import Flask, request, jsonify
from flask_cors import CORS

from dotenv import load_dotenv


load_dotenv()


app = Flask(__name__)

CORS(app)


def get_db_connection():

    connection = pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor
    )

    return connection


@app.route("/api/health", methods=["GET"])
def health():

    try:

        connection = get_db_connection()

        connection.close()

        return jsonify({
            "status": "success",
            "message": "API and database are healthy"
        }), 200

    except Exception as error:

        return jsonify({
            "status": "error",
            "message": "Database connection failed",
            "error": str(error)
        }), 500


@app.route("/api/register", methods=["POST"])
def register():

    data = request.get_json()

    if not data:

        return jsonify({
            "status": "error",
            "message": "Request body is required"
        }), 400

    name = data.get("name")
    email = data.get("email")
    mobile = data.get("mobile")
    community = data.get("community")

    if not name:

        return jsonify({
            "status": "error",
            "message": "Name is required"
        }), 400

    if not email:

        return jsonify({
            "status": "error",
            "message": "Email is required"
        }), 400

    if not mobile:

        return jsonify({
            "status": "error",
            "message": "Mobile number is required"
        }), 400

    if not community:

        return jsonify({
            "status": "error",
            "message": "Community type is required"
        }), 400


    skills = data.get("skills", [])

    skills_json = json.dumps(skills)


    connection = None

    try:

        connection = get_db_connection()

        with connection.cursor() as cursor:

            sql = """
                INSERT INTO registrations
                (
                    name,
                    email,
                    mobile,
                    city,
                    country,
                    company,
                    role,
                    experience,
                    skills,
                    community,
                    comments
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
            """

            cursor.execute(
                sql,
                (
                    name,
                    email,
                    mobile,
                    data.get("city"),
                    data.get("country"),
                    data.get("company"),
                    data.get("role"),
                    data.get("experience"),
                    skills_json,
                    community,
                    data.get("comments")
                )
            )

        connection.commit()

        registration_id = cursor.lastrowid

        return jsonify({
            "status": "success",
            "message": "Registration saved successfully",
            "registration_id": registration_id
        }), 201


    except pymysql.err.IntegrityError:

        return jsonify({
            "status": "error",
            "message": "This email is already registered"
        }), 409


    except Exception as error:

        if connection:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": "Unable to save registration",
            "error": str(error)
        }), 500


    finally:

        if connection:
            connection.close()


@app.route("/api/registrations", methods=["GET"])
def get_registrations():

    connection = None

    try:

        connection = get_db_connection()

        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    name,
                    email,
                    mobile,
                    city,
                    country,
                    company,
                    role,
                    experience,
                    skills,
                    community,
                    comments,
                    created_at
                FROM registrations
                ORDER BY created_at DESC
            """)

            registrations = cursor.fetchall()

        return jsonify({
            "status": "success",
            "count": len(registrations),
            "registrations": registrations
        }), 200


    except Exception as error:

        return jsonify({
            "status": "error",
            "message": "Unable to retrieve registrations",
            "error": str(error)
        }), 500


    finally:

        if connection:
            connection.close()


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
