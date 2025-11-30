const express = require('express');
const router = express.Router();
const { query } = require('../config/database');

// Database diagnostics endpoint
router.get('/diagnostics', async (req, res) => {
  try {
    // Check if tables exist
    const tables = await query(`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public' 
      AND table_name IN ('machine_live_status', 'machine_readings_log')
      ORDER BY table_name
    `);
    
    let liveCount = 0;
    let logCount = 0;
    
    // Try to count records
    try {
      const liveResult = await query('SELECT COUNT(*) as count FROM machine_live_status');
      liveCount = parseInt(liveResult[0].count);
    } catch (e) {
      // Table doesn't exist
    }
    
    try {
      const logResult = await query('SELECT COUNT(*) as count FROM machine_readings_log');
      logCount = parseInt(logResult[0].count);
    } catch (e) {
      // Table doesn't exist
    }
    
    res.json({
      success: true,
      tables: tables.map(t => t.table_name),
      data: {
        machine_live_status_count: liveCount,
        machine_readings_log_count: logCount,
        tables_exist: tables.length === 2
      }
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Get live status of all 4 machines
router.get('/live', async (req, res) => {
  try {
    const liveStatus = await query(
      `SELECT machine_id, data, updated_at 
       FROM machine_live_status 
       ORDER BY machine_id`
    );
    
    res.json({
      success: true,
      data: liveStatus,
      count: liveStatus.length
    });
  } catch (error) {
    console.error('Error fetching live status:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch live status',
      message: error.message
    });
  }
});

// Get live status for specific machine
router.get('/live/:machineId', async (req, res) => {
  try {
    const { machineId } = req.params;
    const status = await query(
      `SELECT machine_id, data, updated_at 
       FROM machine_live_status 
       WHERE machine_id = $1`,
      [machineId]
    );
    
    if (status.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'Machine not found'
      });
    }
    
    res.json({
      success: true,
      data: status[0]
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

// Get historical readings (log) with optional limit
router.get('/readings', async (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 100;
    const readings = await query(
      `SELECT id, data, created_at 
       FROM machine_readings_log 
       ORDER BY created_at DESC 
       LIMIT $1`,
      [limit]
    );
    
    res.json({
      success: true,
      data: readings,
      count: readings.length
    });
  } catch (error) {
    console.error('Error fetching readings:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch readings',
      message: error.message
    });
  }
});

// Get reading by ID from log
router.get('/readings/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const readings = await query(
      'SELECT id, data, created_at FROM machine_readings_log WHERE id = $1',
      [id]
    );
    
    if (readings.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'Reading not found'
      });
    }
    
    res.json({
      success: true,
      data: readings[0]
    });
  } catch (error) {
    console.error('Error fetching reading:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch reading',
      message: error.message
    });
  }
});

// Get historical readings for a specific machine ID
router.get('/machines/:machineId/readings', async (req, res) => {
  try {
    const { machineId } = req.params;
    const limit = parseInt(req.query.limit) || 100;
    
    const readings = await query(
      `SELECT id, data, created_at 
       FROM machine_readings_log 
       WHERE data->>'MachineID' = $1 
       ORDER BY created_at DESC 
       LIMIT $2`,
      [machineId, limit]
    );
    
    if (readings.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'No readings found for this machine'
      });
    }
    
    res.json({
      success: true,
      data: readings,
      count: readings.length
    });
  } catch (error) {
    console.error('Error fetching machine readings:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch machine readings',
      message: error.message
    });
  }
});

// Post new machine reading (writes to both log and live status)
router.post('/readings', async (req, res) => {
  try {
    const { timestamp, MachineID, cycle_number, current, state, door_opened } = req.body;
    
    // Validate required fields
    if (!MachineID || !state) {
      return res.status(400).json({
        success: false,
        error: 'Missing required fields: MachineID and state are required'
      });
    }
    
    const data = {
      timestamp: timestamp || new Date().toISOString(),
      MachineID,
      cycle_number: cycle_number || 0,
      current: current || 0,
      state,
      door_opened: door_opened !== undefined ? door_opened : false
    };
    
    // Insert into log
    const result = await query(
      'INSERT INTO machine_readings_log (data) VALUES ($1) RETURNING id, data, created_at',
      [JSON.stringify(data)]
    );
    
    // Update live status
    await query(
      `INSERT INTO machine_live_status (machine_id, data, updated_at) 
       VALUES ($1, $2, CURRENT_TIMESTAMP)
       ON CONFLICT (machine_id) 
       DO UPDATE SET data = $2, updated_at = CURRENT_TIMESTAMP`,
      [MachineID, JSON.stringify(data)]
    );
    
    res.status(201).json({
      success: true,
      message: 'Reading recorded successfully',
      data: result[0]
    });
  } catch (error) {
    console.error('Error posting reading:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to record reading',
      message: error.message
    });
  }
});

// Get dashboard statistics from live status
router.get('/dashboard', async (req, res) => {
  try {
    const stats = await query(`
      SELECT 
        COUNT(*) as total_machines,
        COUNT(CASE WHEN data->>'state' = 'RUNNING' THEN 1 END) as running_machines,
        COUNT(CASE WHEN data->>'state' = 'IDLE' THEN 1 END) as idle_machines,
        COUNT(CASE WHEN data->>'state' = 'OCCUPIED' THEN 1 END) as occupied_machines,
        AVG(CAST(data->>'current' AS FLOAT)) as avg_current
      FROM machine_live_status
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

// Get list of all 4 machines from live status
router.get('/machines', async (req, res) => {
  try {
    const machines = await query(`
      SELECT 
        machine_id,
        data,
        updated_at as last_reading
      FROM machine_live_status
      ORDER BY machine_id
    `);
    
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

module.exports = router;
