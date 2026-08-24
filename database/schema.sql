CREATE DATABASE IF NOT EXISTS aws_community;

USE aws_community;

CREATE TABLE IF NOT EXISTS registrations (

    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(100) NOT NULL,

    email VARCHAR(150) NOT NULL UNIQUE,

    mobile VARCHAR(20) NOT NULL,

    city VARCHAR(100),

    country VARCHAR(100),

    company VARCHAR(150),

    role VARCHAR(100),

    experience VARCHAR(20),

    skills TEXT,

    community VARCHAR(100) NOT NULL,

    comments TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);
