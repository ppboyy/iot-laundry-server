require('dotenv').config();
const mysql = require('mysql2/promise');
const { Pool } = require('pg');

let db;

// Initialize database connection based on DB_TYPE
const initializeDatabase = async () => {
  const dbType = process.env.DB_TYPE || 'mysql';

  if (dbType === 'mysql') {
    // MySQL/MariaDB connection pool
    db = mysql.createPool({
      host: process.env.DB_HOST,
      port: process.env.DB_PORT || 3306,
      user: process.env.DB_USER,
      password: process.env.DB_PASSWORD,
      database: process.env.DB_NAME,
      waitForConnections: true,
      connectionLimit: 10,
      queueLimit: 0,
      enableKeepAlive: true,
      keepAliveInitialDelay: 0
    });

    // Test connection
    try {
      const connection = await db.getConnection();
      console.log('✓ MySQL database connected successfully');
      connection.release();
    } catch (error) {
      console.error('✗ MySQL connection failed:', error.message);
      throw error;
    }
  } else if (dbType === 'postgres') {
    // PostgreSQL connection pool
    db = new Pool({
      host: process.env.DB_HOST,
      port: process.env.DB_PORT || 5432,
      user: process.env.DB_USER,
      password: process.env.DB_PASSWORD,
      database: process.env.DB_NAME,
      max: 10,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 2000,
      ssl: {
        rejectUnauthorized: false // Required for AWS RDS
      }
    });

    // Test connection
    try {
      const client = await db.connect();
      console.log('✓ PostgreSQL database connected successfully');
      client.release();
    } catch (error) {
      console.error('✗ PostgreSQL connection failed:', error.message);
      throw error;
    }
  } else {
    throw new Error('Invalid DB_TYPE. Must be "mysql" or "postgres"');
  }

  return db;
};

// Query wrapper for both MySQL and PostgreSQL
const query = async (sql, params = []) => {
  const dbType = process.env.DB_TYPE || 'mysql';
  
  try {
    if (dbType === 'mysql') {
      const [rows] = await db.query(sql, params);
      return rows;
    } else if (dbType === 'postgres') {
      const result = await db.query(sql, params);
      return result.rows;
    }
  } catch (error) {
    console.error('Database query error:', error);
    throw error;
  }
};

// Create tables if they don't exist
const createTables = async () => {
  const dbType = process.env.DB_TYPE || 'mysql';
  
  try {
    if (dbType === 'postgres') {
      // Create log table for all historical data
      await query(`
        CREATE TABLE IF NOT EXISTS machine_readings_log (
          id SERIAL PRIMARY KEY,
          data JSONB NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `);
      
      // Create index on MachineID for faster queries
      await query(`
        CREATE INDEX IF NOT EXISTS idx_log_machine_id 
        ON machine_readings_log((data->>'MachineID'))
      `);
      
      // Create live status table for current state of 4 machines
      await query(`
        CREATE TABLE IF NOT EXISTS machine_live_status (
          machine_id VARCHAR(10) PRIMARY KEY,
          data JSONB NOT NULL,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      `);
      
      console.log('✓ Database tables initialized');
    }
  } catch (error) {
    console.error('Error creating tables:', error);
    throw error;
  }
};

module.exports = {
  initializeDatabase,
  createTables,
  getDb: () => db,
  query
};
