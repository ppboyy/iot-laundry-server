const express = require('express');
const router = express.Router();
const { query } = require('../config/database');

// Example: Get all laundry machines
router.get('/machines', async (req, res) => {
  try {
    const machines = await query('SELECT * FROM machines ORDER BY id');
    res.json({
      success: true,
      data: machines,
      count: machines.length
    });
  } catch (error) {
    console.error('Error fetching machines:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch machines',
      message: error.message
    });
  }
});

// Example: Get machine by ID
router.get('/machines/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const machines = await query('SELECT * FROM machines WHERE id = ?', [id]);
    
    if (machines.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'Machine not found'
      });
    }
    
    res.json({
      success: true,
      data: machines[0]
    });
  } catch (error) {
    console.error('Error fetching machine:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch machine',
      message: error.message
    });
  }
});

// Example: Get machine status/logs
router.get('/status', async (req, res) => {
  try {
    // Adjust table name and columns according to your database schema
    const statuses = await query(`
      SELECT * FROM machine_status 
      ORDER BY timestamp DESC 
      LIMIT 100
    `);
    
    res.json({
      success: true,
      data: statuses,
      count: statuses.length
    });
  } catch (error) {
    console.error('Error fetching status:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch status',
      message: error.message
    });
  }
});

// Example: Get latest status for a specific machine
router.get('/machines/:id/status', async (req, res) => {
  try {
    const { id } = req.params;
    const statuses = await query(`
      SELECT * FROM machine_status 
      WHERE machine_id = ? 
      ORDER BY timestamp DESC 
      LIMIT 1
    `, [id]);
    
    if (statuses.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'No status found for this machine'
      });
    }
    
    res.json({
      success: true,
      data: statuses[0]
    });
  } catch (error) {
    console.error('Error fetching machine status:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch machine status',
      message: error.message
    });
  }
});

// Example: Post new machine status (if your IoT devices push data)
router.post('/status', async (req, res) => {
  try {
    const { machine_id, status, temperature, cycle_time } = req.body;
    
    // Validate required fields
    if (!machine_id || !status) {
      return res.status(400).json({
        success: false,
        error: 'Missing required fields: machine_id and status are required'
      });
    }
    
    const result = await query(`
      INSERT INTO machine_status (machine_id, status, temperature, cycle_time, timestamp)
      VALUES (?, ?, ?, ?, NOW())
    `, [machine_id, status, temperature || null, cycle_time || null]);
    
    res.status(201).json({
      success: true,
      message: 'Status recorded successfully',
      data: { id: result.insertId }
    });
  } catch (error) {
    console.error('Error posting status:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to record status',
      message: error.message
    });
  }
});

// Example: Get statistics/dashboard data
router.get('/dashboard', async (req, res) => {
  try {
    // Customize this query based on your actual database schema
    const stats = await query(`
      SELECT 
        COUNT(*) as total_machines,
        SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running_machines,
        SUM(CASE WHEN status = 'idle' THEN 1 ELSE 0 END) as idle_machines,
        SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_machines
      FROM machines
    `);
    
    res.json({
      success: true,
      data: stats[0]
    });
  } catch (error) {
    console.error('Error fetching dashboard data:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch dashboard data',
      message: error.message
    });
  }
});

module.exports = router;
