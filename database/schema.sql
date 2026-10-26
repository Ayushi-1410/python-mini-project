CREATE DATABASE IF NOT EXISTS python_mini_project
		CHARACTER SET utf8mb4
		COLLATE utf8mb4_unicode_ci;

USE python_mini_project;

CREATE TABLE IF NOT EXISTS patients (
		patient_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
		patient_name VARCHAR(100) NOT NULL,
		age TINYINT UNSIGNED NOT NULL,
		gender VARCHAR(30) NOT NULL,
		contact_number VARCHAR(30) NULL,
		department VARCHAR(100) NOT NULL,
		symptoms TEXT NOT NULL,
		priority_level ENUM('Emergency', 'Urgent', 'Normal') NOT NULL,
		-- Temporarily NULL only inside the registration transaction; the app sets it to patient_id before commit.
		queue_number BIGINT UNSIGNED NULL,
		status ENUM('Waiting', 'In Consultation', 'Completed') NOT NULL DEFAULT 'Waiting',
		registered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
		PRIMARY KEY (patient_id),
		UNIQUE KEY uq_patients_queue_number (queue_number),
		KEY idx_patients_active_queue (status, priority_level, registered_at),
		CONSTRAINT chk_patients_age CHECK (age <= 120)
) ENGINE=InnoDB
	DEFAULT CHARSET=utf8mb4
	COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS staff_accounts (
		staff_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
		username VARCHAR(50) NOT NULL,
		email VARCHAR(254) NOT NULL,
		password_hash VARCHAR(255) NOT NULL,
		created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
		PRIMARY KEY (staff_id),
		UNIQUE KEY uq_staff_accounts_username (username),
		UNIQUE KEY uq_staff_accounts_email (email)
) ENGINE=InnoDB
	DEFAULT CHARSET=utf8mb4
	COLLATE=utf8mb4_unicode_ci;
