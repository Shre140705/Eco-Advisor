CREATE DATABASE IF NOT EXISTS ecoadvisor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ecoadvisor;

CREATE TABLE IF NOT EXISTS users (
  user_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  email VARCHAR(255) UNIQUE NULL,
  display_name VARCHAR(120) NULL,
  role ENUM('USER','ADMIN') NOT NULL DEFAULT 'USER',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sources (
  source_id VARCHAR(20) PRIMARY KEY,
  source_type ENUM('LITERATURE','STANDARD','REGULATORY','ASSUMPTION','SYNTHETIC','USER_INPUT') NOT NULL,
  source_title VARCHAR(500) NOT NULL,
  organization VARCHAR(255) NULL,
  publication_year SMALLINT NULL,
  doi_or_url VARCHAR(1000) NULL,
  parameter_scope TEXT NULL,
  verification_status VARCHAR(60) NOT NULL,
  confidence_level ENUM('HIGH','MEDIUM','LOW','UNKNOWN') NOT NULL DEFAULT 'UNKNOWN',
  notes TEXT NULL
);

CREATE TABLE IF NOT EXISTS foods (
  food_id VARCHAR(20) PRIMARY KEY,
  food_name VARCHAR(120) NOT NULL UNIQUE,
  food_category VARCHAR(60) NOT NULL,
  freshness_state ENUM('FRESH','PROCESSED') NOT NULL,
  physical_state ENUM('SOLID','LIQUID','SEMI_SOLID') NOT NULL,
  moisture_level DECIMAL(6,2) NULL,
  fat_content DECIMAL(6,2) NULL,
  ph_value DECIMAL(5,2) NULL,
  perishability DECIMAL(6,2) NULL,
  respiration_rate DECIMAL(6,2) NULL,
  ethylene_sensitivity DECIMAL(6,2) NULL,
  oxygen_sensitivity DECIMAL(6,2) NULL,
  moisture_sensitivity DECIMAL(6,2) NULL,
  light_sensitivity DECIMAL(6,2) NULL,
  default_temperature_c DECIMAL(6,2) NULL,
  default_relative_humidity DECIMAL(6,2) NULL,
  typical_shelf_life_days DECIMAL(8,2) NULL,
  required_oxygen_barrier DECIMAL(6,2) NULL,
  required_moisture_barrier DECIMAL(6,2) NULL,
  required_light_barrier DECIMAL(6,2) NULL,
  mechanical_protection_required DECIMAL(6,2) NULL,
  refrigeration_required BOOLEAN NULL,
  data_status VARCHAR(30) NOT NULL,
  notes TEXT NULL,
  CONSTRAINT chk_food_scores CHECK (moisture_level IS NULL OR moisture_level BETWEEN 0 AND 100)
);

CREATE TABLE IF NOT EXISTS packaging_materials (
  packaging_id VARCHAR(20) PRIMARY KEY,
  material_name VARCHAR(120) NOT NULL UNIQUE,
  packaging_category VARCHAR(60) NOT NULL,
  food_contact_status VARCHAR(40) NOT NULL,
  recycling_method TEXT NULL,
  composting_required BOOLEAN NULL,
  disposal_method TEXT NULL,
  data_status VARCHAR(30) NOT NULL,
  notes TEXT NULL
);

CREATE TABLE IF NOT EXISTS packaging_properties (
  property_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  packaging_id VARCHAR(20) NOT NULL,
  oxygen_barrier DECIMAL(6,2) NULL,
  moisture_barrier DECIMAL(6,2) NULL,
  light_barrier DECIMAL(6,2) NULL,
  mechanical_strength DECIMAL(6,2) NULL,
  flexibility DECIMAL(6,2) NULL,
  heat_resistance DECIMAL(6,2) NULL,
  acidic_food_compatibility DECIMAL(6,2) NULL,
  high_moisture_compatibility DECIMAL(6,2) NULL,
  oily_food_compatibility DECIMAL(6,2) NULL,
  liquid_food_compatibility DECIMAL(6,2) NULL,
  carbon_footprint_score DECIMAL(6,2) NULL,
  recyclability DECIMAL(6,2) NULL,
  recycled_content DECIMAL(6,2) NULL,
  biodegradability DECIMAL(6,2) NULL,
  compostability DECIMAL(6,2) NULL,
  reusability DECIMAL(6,2) NULL,
  material_circularity DECIMAL(6,2) NULL,
  relative_cost DECIMAL(6,2) NULL,
  material_recovery_potential DECIMAL(6,2) NULL,
  confidence_level VARCHAR(20) NOT NULL,
  condition_note TEXT NULL,
  source_id VARCHAR(20) NULL,
  FOREIGN KEY (packaging_id) REFERENCES packaging_materials(packaging_id),
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS recommendations (
  recommendation_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NULL,
  food_id VARCHAR(20) NULL,
  request_json JSON NOT NULL,
  result_json JSON NOT NULL,
  model_version VARCHAR(120) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(user_id),
  FOREIGN KEY (food_id) REFERENCES foods(food_id)
);

CREATE TABLE IF NOT EXISTS model_predictions (
  prediction_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  recommendation_id BIGINT NULL,
  model_version VARCHAR(120) NOT NULL,
  feature_json JSON NOT NULL,
  predicted_value DECIMAL(10,3) NOT NULL,
  data_status VARCHAR(30) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (recommendation_id) REFERENCES recommendations(recommendation_id)
);
