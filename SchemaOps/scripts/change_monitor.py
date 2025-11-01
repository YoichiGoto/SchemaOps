#!/usr/bin/env python3
"""
API-based change monitoring and notification system.
Monitors schema changes from marketplace APIs and triggers notifications.
"""
import json
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChangeMonitor:
    """Monitors schema changes from marketplace APIs."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(exist_ok=True)
        self.schema_history_file = data_dir / "schema_history.json"
        self.change_log_file = data_dir / "change_log.json"
        
        # Load existing data
        self.schema_history = self._load_json_file(self.schema_history_file, {})
        self.change_log = self._load_json_file(self.change_log_file, [])
    
    def _load_json_file(self, file_path: Path, default_value):
        """Load JSON file with error handling."""
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
        return default_value
    
    def _save_json_file(self, file_path: Path, data):
        """Save JSON file with error handling."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving {file_path}: {e}")
    
    def _calculate_schema_hash(self, schema: Dict[str, Any]) -> str:
        """Calculate hash of schema for change detection."""
        # Create a normalized version of the schema for hashing
        normalized = {
            "attributes": sorted(schema.get("attributes", []), key=lambda x: x.get("name", "")),
            "version": schema.get("version", ""),
            "source": schema.get("source", "")
        }
        
        schema_str = json.dumps(normalized, sort_keys=True)
        return hashlib.md5(schema_str.encode()).hexdigest()
    
    def detect_changes(self, mp_name: str, new_schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect changes between current and new schema."""
        changes = []
        
        # Get current schema hash
        current_hash = self.schema_history.get(mp_name, {}).get("hash", "")
        new_hash = self._calculate_schema_hash(new_schema)
        
        if current_hash != new_hash:
            # Schema has changed
            current_schema = self.schema_history.get(mp_name, {}).get("schema", {})
            
            # Compare attributes
            current_attrs = {attr["name"]: attr for attr in current_schema.get("attributes", [])}
            new_attrs = {attr["name"]: attr for attr in new_schema.get("attributes", [])}
            
            # Check for added attributes
            for attr_name, attr_data in new_attrs.items():
                if attr_name not in current_attrs:
                    changes.append({
                        "type": "attribute_added",
                        "attribute": attr_name,
                        "details": attr_data,
                        "severity": "major" if attr_data.get("required", False) else "minor"
                    })
            
            # Check for removed attributes
            for attr_name, attr_data in current_attrs.items():
                if attr_name not in new_attrs:
                    changes.append({
                        "type": "attribute_removed",
                        "attribute": attr_name,
                        "details": attr_data,
                        "severity": "critical" if attr_data.get("required", False) else "major"
                    })
            
            # Check for modified attributes
            for attr_name in current_attrs.keys() & new_attrs.keys():
                current_attr = current_attrs[attr_name]
                new_attr = new_attrs[attr_name]
                
                # Check for changes in properties
                for prop in ["required", "dataType", "maxLength", "description"]:
                    if current_attr.get(prop) != new_attr.get(prop):
                        changes.append({
                            "type": "attribute_modified",
                            "attribute": attr_name,
                            "property": prop,
                            "old_value": current_attr.get(prop),
                            "new_value": new_attr.get(prop),
                            "severity": "critical" if prop == "required" and new_attr.get(prop) else "major"
                        })
            
            # Update schema history
            self.schema_history[mp_name] = {
                "hash": new_hash,
                "schema": new_schema,
                "lastUpdated": datetime.now().isoformat()
            }
            
            logger.info(f"Detected {len(changes)} changes in {mp_name}")
        
        return changes
    
    def log_changes(self, mp_name: str, changes: List[Dict[str, Any]]):
        """Log detected changes to change log."""
        for change in changes:
            change_entry = {
                "id": f"{mp_name}_{int(time.time())}_{hash(change['type'] + change['attribute'])}",
                "mp_name": mp_name,
                "change_type": change["type"],
                "attribute": change.get("attribute", ""),
                "severity": change["severity"],
                "details": change,
                "detected_at": datetime.now().isoformat(),
                "status": "new",
                "sla_hours": self._get_sla_hours(change["severity"]),
                "eta": (datetime.now() + timedelta(hours=self._get_sla_hours(change["severity"]))).isoformat()
            }
            
            self.change_log.append(change_entry)
        
        # Save updated change log
        self._save_json_file(self.change_log_file, self.change_log)
        
        # Save updated schema history
        self._save_json_file(self.schema_history_file, self.schema_history)
    
    def _get_sla_hours(self, severity: str) -> int:
        """Get SLA hours based on severity."""
        sla_map = {
            "critical": 24,
            "major": 72,
            "minor": 168  # 1 week
        }
        return sla_map.get(severity, 168)
    
    def get_pending_changes(self) -> List[Dict[str, Any]]:
        """Get all pending changes that need attention."""
        return [change for change in self.change_log if change["status"] == "new"]
    
    def get_overdue_changes(self) -> List[Dict[str, Any]]:
        """Get changes that are overdue based on SLA."""
        now = datetime.now()
        overdue = []
        
        for change in self.change_log:
            if change["status"] == "new":
                eta = datetime.fromisoformat(change["eta"])
                if now > eta:
                    overdue.append(change)
        
        return overdue
    
    def update_change_status(self, change_id: str, status: str, notes: str = ""):
        """Update the status of a change."""
        for change in self.change_log:
            if change["id"] == change_id:
                change["status"] = status
                change["updated_at"] = datetime.now().isoformat()
                if notes:
                    change["notes"] = notes
                break
        
        self._save_json_file(self.change_log_file, self.change_log)
    
    def generate_change_report(self) -> Dict[str, Any]:
        """Generate a summary report of all changes."""
        total_changes = len(self.change_log)
        pending_changes = len(self.get_pending_changes())
        overdue_changes = len(self.get_overdue_changes())
        
        # Group by severity
        severity_counts = {"critical": 0, "major": 0, "minor": 0}
        for change in self.change_log:
            severity = change["severity"]
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        # Group by MP
        mp_counts = {}
        for change in self.change_log:
            mp_name = change["mp_name"]
            mp_counts[mp_name] = mp_counts.get(mp_name, 0) + 1
        
        return {
            "summary": {
                "total_changes": total_changes,
                "pending_changes": pending_changes,
                "overdue_changes": overdue_changes,
                "resolved_changes": total_changes - pending_changes
            },
            "severity_breakdown": severity_counts,
            "mp_breakdown": mp_counts,
            "generated_at": datetime.now().isoformat()
        }

class NotificationService:
    """Handles notifications for schema changes."""
    
    def __init__(self, monitor: ChangeMonitor):
        self.monitor = monitor
    
    def send_critical_alert(self, changes: List[Dict[str, Any]]):
        """Send immediate alert for critical changes."""
        logger.critical(f"CRITICAL ALERT: {len(changes)} critical schema changes detected")
        
        for change in changes:
            logger.critical(f"- {change['mp_name']}: {change['change_type']} on {change['attribute']}")
    
    def send_daily_summary(self):
        """Send daily summary of all changes."""
        report = self.monitor.generate_change_report()
        
        logger.info("=== DAILY CHANGE SUMMARY ===")
        logger.info(f"Total changes: {report['summary']['total_changes']}")
        logger.info(f"Pending: {report['summary']['pending_changes']}")
        logger.info(f"Overdue: {report['summary']['overdue_changes']}")
        
        if report['summary']['overdue_changes'] > 0:
            logger.warning(f"WARNING: {report['summary']['overdue_changes']} changes are overdue!")
    
    def send_sla_reminder(self):
        """Send reminders for changes approaching SLA deadline."""
        pending_changes = self.monitor.get_pending_changes()
        now = datetime.now()
        
        for change in pending_changes:
            eta = datetime.fromisoformat(change["eta"])
            hours_remaining = (eta - now).total_seconds() / 3600
            
            if hours_remaining <= 24 and hours_remaining > 0:
                logger.warning(f"SLA REMINDER: {change['mp_name']} change due in {hours_remaining:.1f} hours")

def main():
    """Main execution function."""
    # Initialize monitor
    data_dir = Path(__file__).parent.parent / "20_QA" / "monitoring"
    monitor = ChangeMonitor(data_dir)
    
    # Load latest schemas (simulate API calls)
    schema_files = [
        "google_merchant_center_schema.json",
        "amazon_sp_api_schema.json",
        "shopify_admin_api_schema.json"
    ]
    
    notification_service = NotificationService(monitor)
    
    # Process each schema
    for schema_file in schema_files:
        schema_path = Path(__file__).parent.parent / "20_QA" / schema_file
        if schema_path.exists():
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            
            mp_name = schema_file.replace("_schema.json", "")
            changes = monitor.detect_changes(mp_name, schema)
            
            if changes:
                monitor.log_changes(mp_name, changes)
                
                # Send critical alerts
                critical_changes = [c for c in changes if c["severity"] == "critical"]
                if critical_changes:
                    notification_service.send_critical_alert(critical_changes)
    
    # Generate reports
    report = monitor.generate_change_report()
    
    # Save report
    report_file = data_dir / "change_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # Send notifications
    notification_service.send_daily_summary()
    notification_service.send_sla_reminder()
    
    print(f"\n=== CHANGE MONITORING SUMMARY ===")
    print(f"Total changes tracked: {report['summary']['total_changes']}")
    print(f"Pending changes: {report['summary']['pending_changes']}")
    print(f"Overdue changes: {report['summary']['overdue_changes']}")
    
    if report['summary']['overdue_changes'] > 0:
        print(f"⚠️  WARNING: {report['summary']['overdue_changes']} changes are overdue!")
    
    print(f"\nSeverity breakdown:")
    for severity, count in report['severity_breakdown'].items():
        print(f"- {severity}: {count}")
    
    print(f"\nMP breakdown:")
    for mp_name, count in report['mp_breakdown'].items():
        print(f"- {mp_name}: {count}")

if __name__ == "__main__":
    main()





