CREATE DATABASE IF NOT EXISTS medicore_hms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE medicore_hms;
CREATE TABLE IF NOT EXISTS users(
 id INT AUTO_INCREMENT PRIMARY KEY, full_name VARCHAR(120) NOT NULL,
 email VARCHAR(190) UNIQUE NOT NULL, password_hash VARCHAR(255) NOT NULL,
 role ENUM('Admin','Doctor','Receptionist','Pharmacist','Lab Staff') DEFAULT 'Receptionist',
 is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS patients(
 id INT AUTO_INCREMENT PRIMARY KEY, full_name VARCHAR(120) NOT NULL, email VARCHAR(190),
 phone VARCHAR(30), gender VARCHAR(20), date_of_birth DATE, blood_group VARCHAR(5),
 address TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS doctors(
 id INT AUTO_INCREMENT PRIMARY KEY, full_name VARCHAR(120) NOT NULL, email VARCHAR(190),
 phone VARCHAR(30), specialization VARCHAR(100), consultation_fee DECIMAL(10,2) DEFAULT 0,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS appointments(
 id INT AUTO_INCREMENT PRIMARY KEY, patient_id INT NOT NULL, doctor_id INT NOT NULL,
 appointment_date DATE NOT NULL, appointment_time TIME NOT NULL, reason TEXT,
 status ENUM('Scheduled','Completed','Cancelled','No-show') DEFAULT 'Scheduled',
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(patient_id) REFERENCES patients(id), FOREIGN KEY(doctor_id) REFERENCES doctors(id),
 INDEX idx_appointment_date(appointment_date)
);
CREATE TABLE IF NOT EXISTS bills(
 id INT AUTO_INCREMENT PRIMARY KEY, patient_id INT NOT NULL, description VARCHAR(255),
 amount DECIMAL(10,2) NOT NULL, payment_status ENUM('Unpaid','Paid','Partially Paid') DEFAULT 'Unpaid',
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(patient_id) REFERENCES patients(id)
);
CREATE TABLE IF NOT EXISTS medicines(
 id INT AUTO_INCREMENT PRIMARY KEY, medicine_name VARCHAR(150) NOT NULL, category VARCHAR(100),
 quantity INT NOT NULL DEFAULT 0, unit_price DECIMAL(10,2) NOT NULL DEFAULT 0,
 expiry_date DATE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS lab_tests(
 id INT AUTO_INCREMENT PRIMARY KEY, patient_id INT NOT NULL, test_name VARCHAR(150) NOT NULL,
 test_date DATE NOT NULL, result TEXT, status ENUM('Pending','In Progress','Completed') DEFAULT 'Pending',
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(patient_id) REFERENCES patients(id)
);
