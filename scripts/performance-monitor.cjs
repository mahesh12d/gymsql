#!/usr/bin/env node

const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

class PerformanceMonitor {
  constructor() {
    this.startTime = Date.now();
    this.metrics = {
      startup: {},
      resources: {},
      database: {},
      components: {},
      environment: {
        platform: os.platform(),
        arch: os.arch(),
        nodeVersion: process.version,
        totalMemory: Math.round(os.totalmem() / 1024 / 1024) + 'MB',
        cpuCount: os.cpus().length,
        isReplit: !!process.env.REPLIT_DEPLOYMENT
      }
    };
    this.logFile = path.join(process.cwd(), 'performance-log.json');
  }

  // Track timing for different startup phases
  trackStartupPhase(phase, startTime, endTime = Date.now()) {
    const duration = endTime - startTime;
    this.metrics.startup[phase] = {
      duration: `${duration}ms`,
      timestamp: new Date().toISOString()
    };
    console.log(`⏱️  ${phase}: ${duration}ms`);
    return duration;
  }

  // Monitor system resources
  trackResources() {
    const used = process.memoryUsage();
    const loadAvg = os.loadavg();
    
    this.metrics.resources = {
      memory: {
        rss: Math.round(used.rss / 1024 / 1024) + 'MB',
        heapTotal: Math.round(used.heapTotal / 1024 / 1024) + 'MB',
        heapUsed: Math.round(used.heapUsed / 1024 / 1024) + 'MB',
        external: Math.round(used.external / 1024 / 1024) + 'MB'
      },
      system: {
        freeMemory: Math.round(os.freemem() / 1024 / 1024) + 'MB',
        loadAverage: loadAvg.map(load => load.toFixed(2)),
        uptime: Math.round(os.uptime()) + 's'
      }
    };
    
    console.log(`💾 Memory Usage: ${this.metrics.resources.memory.rss} RSS, ${this.metrics.resources.memory.heapUsed} Heap`);
    console.log(`⚡ Load Average: [${this.metrics.resources.system.loadAverage.join(', ')}]`);
  }

  // Test database connection performance
  async trackDatabasePerformance() {
    console.log('🗄️  Testing database connection...');
    const dbStart = Date.now();
    
    try {
      // Test if PostgreSQL is accessible
      const result = spawnSync('python3.11', ['-c', `
import time, psycopg2, os
from urllib.parse import urlparse

start_time = time.time()
try:
    # Use DATABASE_URL if available, otherwise default connection
    db_url = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/postgres')
    
    # Parse connection details
    parsed = urlparse(db_url)
    conn = psycopg2.connect(
        host=parsed.hostname or 'localhost',
        port=parsed.port or 5432,
        database=parsed.path[1:] if parsed.path else 'postgres',
        user=parsed.username or 'postgres',
        password=parsed.password or ''
    )
    
    # Test query
    cursor = conn.cursor()
    cursor.execute('SELECT version();')
    version = cursor.fetchone()[0]
    
    connection_time = (time.time() - start_time) * 1000
    print(f"CONNECTION_TIME:{connection_time:.2f}")
    print(f"DB_VERSION:{version}")
    
    cursor.close()
    conn.close()
    print("STATUS:SUCCESS")
except Exception as e:
    connection_time = (time.time() - start_time) * 1000
    print(f"CONNECTION_TIME:{connection_time:.2f}")
    print(f"ERROR:{str(e)}")
    print("STATUS:FAILED")
      `], { encoding: 'utf-8', timeout: 10000 });

      const output = result.stdout;
      const lines = output.split('\n').filter(line => line.trim());
      
      let connectionTime = 'N/A';
      let dbVersion = 'Unknown';
      let status = 'FAILED';
      
      lines.forEach(line => {
        if (line.startsWith('CONNECTION_TIME:')) connectionTime = line.split(':')[1] + 'ms';
        if (line.startsWith('DB_VERSION:')) dbVersion = line.split(':')[1];
        if (line.startsWith('STATUS:')) status = line.split(':')[1];
      });

      this.metrics.database = {
        connectionTime,
        version: dbVersion,
        status,
        totalTestTime: `${Date.now() - dbStart}ms`
      };

      console.log(`🗄️  Database connection: ${connectionTime} (${status})`);
      
    } catch (error) {
      this.metrics.database = {
        connectionTime: `${Date.now() - dbStart}ms`,
        status: 'ERROR',
        error: error.message
      };
      console.log(`❌ Database test failed: ${error.message}`);
    }
  }

  // Track component loading times
  async trackComponentLoading() {
    console.log('📦 Testing component loading...');
    const componentStart = Date.now();
    
    // Test Python import times
    const pythonImportStart = Date.now();
    const pythonResult = spawnSync('python3.11', ['-c', `
import time
import sys
start_time = time.time()

# Test critical imports
try:
    import fastapi
    fastapi_time = (time.time() - start_time) * 1000
    
    import sqlalchemy
    sqlalchemy_time = (time.time() - start_time) * 1000
    
    import pydantic
    pydantic_time = (time.time() - start_time) * 1000
    
    print(f"FASTAPI_IMPORT:{fastapi_time:.2f}")
    print(f"SQLALCHEMY_IMPORT:{sqlalchemy_time:.2f}")
    print(f"PYDANTIC_IMPORT:{pydantic_time:.2f}")
    print("PYTHON_STATUS:SUCCESS")
except Exception as e:
    print(f"PYTHON_ERROR:{str(e)}")
    print("PYTHON_STATUS:FAILED")
    `], { encoding: 'utf-8', timeout: 15000 });

    const pythonOutput = pythonResult.stdout;
    const pythonLines = pythonOutput.split('\n').filter(line => line.trim());
    
    const pythonMetrics = {};
    pythonLines.forEach(line => {
      if (line.includes('_IMPORT:')) {
        const [key, value] = line.split(':');
        pythonMetrics[key.toLowerCase().replace('_import', '')] = value + 'ms';
      }
    });

    this.metrics.components = {
      python: {
        ...pythonMetrics,
        totalLoadTime: `${Date.now() - pythonImportStart}ms`
      },
      node: {
        startupTime: `${Date.now() - componentStart}ms`
      }
    };

    console.log(`🐍 Python imports: FastAPI ${pythonMetrics.fastapi || 'N/A'}, SQLAlchemy ${pythonMetrics.sqlalchemy || 'N/A'}`);
  }

  // Save metrics to file
  saveMetrics() {
    const totalTime = Date.now() - this.startTime;
    this.metrics.summary = {
      totalMonitoringTime: `${totalTime}ms`,
      timestamp: new Date().toISOString(),
      recommendations: this.generateRecommendations()
    };

    try {
      fs.writeFileSync(this.logFile, JSON.stringify(this.metrics, null, 2));
      console.log(`\n📊 Performance report saved to: ${this.logFile}`);
    } catch (error) {
      console.log(`❌ Failed to save metrics: ${error.message}`);
    }
  }

  // Generate performance recommendations
  generateRecommendations() {
    const recommendations = [];
    
    // Check database connection time
    if (this.metrics.database.connectionTime) {
      const dbTime = parseFloat(this.metrics.database.connectionTime);
      if (dbTime > 1000) {
        recommendations.push("Database connection is slow (>1s). Consider keeping connection pool alive.");
      }
    }

    // Check memory usage
    if (this.metrics.resources.memory) {
      const heapUsed = parseInt(this.metrics.resources.memory.heapUsed);
      if (heapUsed > 512) {
        recommendations.push("High memory usage detected. Monitor for memory leaks.");
      }
    }

    // Environment-specific recommendations
    if (this.metrics.environment.isReplit) {
      recommendations.push("Running on Replit - optimized cloud environment detected.");
    } else {
      recommendations.push("Running locally - consider using SSD storage and closing unnecessary applications.");
    }

    return recommendations;
  }

  // Display summary
  displaySummary() {
    console.log('\n' + '='.repeat(60));
    console.log('🚀 PERFORMANCE MONITORING SUMMARY');
    console.log('='.repeat(60));
    
    console.log(`\n🌍 Environment: ${this.metrics.environment.isReplit ? 'Replit Cloud' : 'Local Development'}`);
    console.log(`💻 System: ${this.metrics.environment.platform} ${this.metrics.environment.arch}`);
    console.log(`⚡ CPUs: ${this.metrics.environment.cpuCount} cores`);
    console.log(`💾 Total Memory: ${this.metrics.environment.totalMemory}`);
    
    if (this.metrics.database.connectionTime) {
      console.log(`\n🗄️  Database Performance:`);
      console.log(`   Connection Time: ${this.metrics.database.connectionTime}`);
      console.log(`   Status: ${this.metrics.database.status}`);
    }
    
    if (this.metrics.components.python) {
      console.log(`\n📦 Component Loading:`);
      Object.entries(this.metrics.components.python).forEach(([key, value]) => {
        if (key !== 'totalLoadTime') {
          console.log(`   ${key.charAt(0).toUpperCase() + key.slice(1)}: ${value}`);
        }
      });
    }
    
    console.log(`\n💡 Recommendations:`);
    this.metrics.summary.recommendations.forEach(rec => {
      console.log(`   • ${rec}`);
    });
    
    console.log('\n' + '='.repeat(60));
  }

  // Run complete monitoring suite
  async runFullMonitoring() {
    console.log('🔍 Starting Performance Monitoring...\n');
    
    const phases = [
      { name: 'Initial Setup', fn: () => this.trackResources() },
      { name: 'Database Connection Test', fn: () => this.trackDatabasePerformance() },
      { name: 'Component Loading Test', fn: () => this.trackComponentLoading() },
      { name: 'Final Resource Check', fn: () => this.trackResources() }
    ];

    for (const phase of phases) {
      const phaseStart = Date.now();
      try {
        await phase.fn();
        this.trackStartupPhase(phase.name, phaseStart);
      } catch (error) {
        console.log(`❌ ${phase.name} failed: ${error.message}`);
        this.trackStartupPhase(`${phase.name} (FAILED)`, phaseStart);
      }
      console.log(''); // Add spacing between phases
    }

    this.saveMetrics();
    this.displaySummary();
  }
}

// CLI interface
if (require.main === module) {
  const monitor = new PerformanceMonitor();
  
  const command = process.argv[2];
  
  if (command === 'quick') {
    // Quick check - just resources and database
    monitor.trackResources();
    monitor.trackDatabasePerformance().then(() => {
      monitor.saveMetrics();
      console.log('\nQuick performance check completed');
    });
  } else if (command === 'watch') {
    // Continuous monitoring
    console.log('👀 Starting continuous monitoring (Ctrl+C to stop)...\n');
    setInterval(() => {
      console.log(`\n📊 ${new Date().toLocaleTimeString()}`);
      monitor.trackResources();
    }, 5000);
  } else {
    // Full monitoring suite
    monitor.runFullMonitoring().catch(error => {
      console.error('❌ Monitoring failed:', error.message);
      process.exit(1);
    });
  }
}

module.exports = PerformanceMonitor;