-- CRM Database Schema
-- Run this once against your MySQL database (Aiven, or any MySQL server)
-- Example: mysql -h HOST -P PORT -u USER -p DBNAME < schema.sql

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS leads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150),
    phone VARCHAR(30),
    company VARCHAR(150),
    website VARCHAR(150),
    logo_url VARCHAR(255),
    source VARCHAR(80) DEFAULT 'Other',
    status ENUM('New', 'Contacted', 'Qualified', 'Proposal', 'Won', 'Lost') DEFAULT 'New',
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lead_id INT NOT NULL,
    note_text TEXT NOT NULL,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_name ON leads(name);
