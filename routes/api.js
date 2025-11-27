const express = require('express');
const router = express.Router();
const { query } = require('../config/database');

// Get all machine readings with optional limit
router.get('/readings', async (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 100;
    const readings = await query(
      `SELECT id, data, created_at 
       FROM machine_readings 
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

// Get reading by ID
router.get('/readings/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const readings = await query(
      'SELECT id, data, created_at FROM machine_readings WHERE id = $1',
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

// Get readings for a specific machine ID
router.get('/machines/:machineId/readings', async (req, res) => {
  try {
    const { machineId } = req.params;
    const limit = parseInt(req.query.limit) || 100;
    
    const readings = await query(
      `SELECT id, data, created_at 
       FROM machine_readings 
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

// Get latest reading for a specific machine
router.get('/machines/:machineId/latest', async (req, res) => {
  try {
    const { machineId } = req.params;
    
    const readings = await query(
      `SELECT id, data, created_at 
       FROM machine_readings 
       WHERE data->>'MachineID' = $1 
       ORDER BY created_at DESC 
       LIMIT 1`,
      [machineId]
    );
    
    if (readings.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'No readings found for this machine'
      });
    }
    
    res.json({
      success: true,
      data: readings[0]
    });
  } catch (error) {
    console.error('Error fetching latest reading:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch latest reading',
      message: error.message
    });
  }
});

// Post new machine reading
router.post('/readings', async (req, res) => {
  try {
    const { timestamp, MachineID, cycle_number, current, state } = req.body;
    
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
      state
    };
    
    const result = await query(
      'INSERT INTO machine_readings (data) VALUES ($1) RETURNING id, data, created_at',
      [JSON.stringify(data)]
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

// Get dashboard statistics
router.get('/dashboard', async (req, res) => {
  try {
    // Get latest reading for each unique machine
    const stats = await query(`
      WITH latest_readings AS (
        SELECT DISTINCT ON (data->>'MachineID')
          data->>'MachineID' as machine_id,
          data->>'state' as state,
          data->>'current' as current,
          data->>'cycle_number' as cycle_number,
          created_at
        FROM machine_readings
        ORDER BY data->>'MachineID', created_at DESC
      )
      SELECT 
        COUNT(*) as total_machines,
        COUNT(CASE WHEN state = 'RUNNING' THEN 1 END) as running_machines,
        COUNT(CASE WHEN state = 'IDLE' THEN 1 END) as idle_machines,
        COUNT(CASE WHEN state = 'ERROR' THEN 1 END) as error_machines,
        AVG(CAST(current AS FLOAT)) as avg_current
      FROM latest_readings
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

// Get list of all unique machines
router.get('/machines', async (req, res) => {
  try {
    const machines = await query(`
      SELECT DISTINCT 
        data->>'MachineID' as machine_id,
        MAX(created_at) as last_reading
      FROM machine_readings
      GROUP BY data->>'MachineID'
      ORDER BY last_reading DESC
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
