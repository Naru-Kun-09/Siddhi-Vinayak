CREATE DATABASE IF NOT EXISTS siddhivinayak_pro;
USE siddhivinayak_pro;

-- Table 1: users
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(255) UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('TRUSTEE', 'ASSISTANT', 'ATTENDANT', 'SCANNER', 'ADMIN') NOT NULL,
    parent_trustee_id INT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_trustee_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Table 2: passes
CREATE TABLE passes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trustee_id INT NOT NULL,
    assistant_id INT NULL,
    visitor_name VARCHAR(255) NOT NULL,
    visitor_phone VARCHAR(20) NOT NULL,
    visitor_email VARCHAR(255),
    total_people INT NOT NULL,
    darshan_type ENUM('VIP', 'VASTRA', 'ESCORT', 'NORMAL') NOT NULL,
    vastra_count INT NULL,
    vastra_names JSON NULL,
    date DATE NOT NULL,
    time TIME NOT NULL,
    grace_minutes INT NOT NULL,
    assigned_attendant_id INT NULL,
    trustee_note VARCHAR(100),
    attendant_notes JSON NULL,
    qr_code_string VARCHAR(255) UNIQUE NOT NULL,
    status ENUM('NOT_CONTACTED', 'CONTACTED', 'CONFIRMED', 'REACHED', 'AT_GATE', 'COMPLETED', 'CANCELLED', 'EXPIRED', 'ISSUE') DEFAULT 'NOT_CONTACTED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (trustee_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (assistant_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_attendant_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Table 3: attendant_attendance
CREATE TABLE attendant_attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    attendant_id INT NOT NULL,
    date DATE NOT NULL,
    time_in TIMESTAMP NULL,
    time_out TIMESTAMP NULL,
    total_hours FLOAT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (attendant_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_attendance (attendant_id, date)
);

-- Table 4: scans
CREATE TABLE scans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pass_id INT NOT NULL,
    stage ENUM('ARRIVED', 'AT_GATE', 'COMPLETED') NOT NULL,
    source ENUM('SCANNER', 'ATTENDANT') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pass_id) REFERENCES passes(id) ON DELETE CASCADE
);

-- Table 5: issues
CREATE TABLE issues (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pass_id INT NOT NULL,
    reported_by_user_id INT NOT NULL,
    issue_type ENUM('LATE', 'DUPLICATE_QR', 'NO_SHOW', 'OTHER') NOT NULL,
    description VARCHAR(255),
    status ENUM('OPEN', 'RESOLVED') DEFAULT 'OPEN',
    resolved_by_user_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (pass_id) REFERENCES passes(id) ON DELETE CASCADE,
    FOREIGN KEY (reported_by_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (resolved_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Table 6: aarti
CREATE TABLE aarti (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name ENUM('KAKAD', 'MADHYAN', 'DHOOP', 'SHEJ') NOT NULL,
    date DATE NOT NULL,
    total_capacity INT NOT NULL,
    booked_capacity INT DEFAULT 0,
    status ENUM('OPEN', 'CLOSED') DEFAULT 'OPEN',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Table 7: settings
CREATE TABLE settings (
    id INT PRIMARY KEY DEFAULT 1,
    grace_minutes_default INT DEFAULT 30,
    reminder_config JSON NULL,
    max_visitors_per_attendant INT DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Table 8: logs
CREATE TABLE logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(255) NOT NULL,
    entity_type ENUM('PASS', 'USER', 'AARTI', 'SETTINGS', 'OTHER') NOT NULL,
    entity_id INT NULL,
    payload JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Insert default settings
INSERT INTO settings (id, grace_minutes_default, max_visitors_per_attendant) VALUES (1, 30, 10);
