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

module.exports = {
  initializeDatabase,
  getDb: () => db,
  query
};
