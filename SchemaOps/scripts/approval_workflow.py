#!/usr/bin/env python3
"""
Approval workflow automation for schema changes (TRAM Review step).
Manages proposal creation, review, application. Requires correction reason on modify/reject.
Saves feedback to feedback_store for model improvement.
"""
import json
import csv
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

class ApprovalWorkflow:
    def __init__(self, approval_sheet_path: Path, feedback_store_path: Optional[Path] = None):
        self.approval_sheet_path = approval_sheet_path
        self.feedback_store_path = feedback_store_path or (approval_sheet_path.parent.parent / "20_QA" / "feedback_store.json")
        self.proposals = self._load_proposals()
    
    def _load_proposals(self) -> List[Dict[str, Any]]:
        """Load existing proposals from CSV."""
        if not self.approval_sheet_path.exists():
            return []
        
        proposals = []
        with open(self.approval_sheet_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                proposals.append(row)
        return proposals
    
    def create_proposal(self, target_sheet: str, change_type: str, 
                       change_details: Dict[str, Any], proposer: str) -> str:
        """Create a new proposal."""
        proposal_id = f"PROP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        proposal = {
            'proposalId': proposal_id,
            'targetSheet': target_sheet,
            'changeType': change_type,
            'changeDetails': json.dumps(change_details, ensure_ascii=False),
            'proposer': proposer,
            'proposedAt': datetime.now().isoformat(),
            'reviewer': '',
            'status': 'pending',
            'reviewedAt': '',
            'reviewNotes': '',
            'appliedAt': ''
        }
        
        self.proposals.append(proposal)
        self._save_proposals()
        
        return proposal_id
    
    def review_proposal(self, proposal_id: str, reviewer: str, 
                       status: str, review_notes: str = '',
                       correction_reason: str = '',
                       task_context: Optional[Dict] = None,
                       retrieved_authorities: Optional[List] = None,
                       final_outcome: Optional[Dict] = None) -> bool:
        """
        Review a proposal (approve/reject/modified).
        When status is 'rejected' or 'modified', correction_reason is required for feedback_store.
        """
        if status in ('rejected', 'modified') and not correction_reason:
            raise ValueError("correction_reason is required when status is rejected or modified")

        for proposal in self.proposals:
            if proposal['proposalId'] == proposal_id:
                proposal['reviewer'] = reviewer
                proposal['status'] = status
                proposal['reviewedAt'] = datetime.now().isoformat()
                proposal['reviewNotes'] = review_notes
                if correction_reason:
                    proposal['correctionReason'] = correction_reason

                if status in ('rejected', 'modified') and correction_reason:
                    self._save_feedback(
                        proposal_id=proposal_id,
                        status=status,
                        reason=correction_reason,
                        task_context=task_context,
                        retrieved_authorities=retrieved_authorities,
                        final_outcome=final_outcome,
                        marketplace=proposal.get('marketplace'),
                        category=proposal.get('category'),
                    )

                self._save_proposals()
                return True

        return False

    def _save_feedback(self, proposal_id: str, status: str, reason: str,
                       task_context: Optional[Dict] = None,
                       retrieved_authorities: Optional[List] = None,
                       final_outcome: Optional[Dict] = None,
                       marketplace: Optional[str] = None,
                       category: Optional[str] = None):
        """Append feedback to feedback_store.json for model improvement."""
        self.feedback_store_path.parent.mkdir(parents=True, exist_ok=True)
        feedback = {
            "proposalId": proposal_id,
            "status": status,
            "reason": reason,
            "taskContext": task_context,
            "retrievedAuthorities": retrieved_authorities,
            "finalOutcome": final_outcome,
            "marketplace": marketplace,
            "category": category,
            "recordedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        existing = []
        if self.feedback_store_path.exists():
            try:
                with open(self.feedback_store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                existing = data if isinstance(data, list) else data.get("feedback", [])
            except Exception:
                pass
        existing.append(feedback)
        with open(self.feedback_store_path, "w", encoding="utf-8") as f:
            json.dump({"feedback": existing}, f, ensure_ascii=False, indent=2)
    
    def apply_proposal(self, proposal_id: str) -> bool:
        """Apply an approved proposal to target sheet."""
        proposal = None
        for p in self.proposals:
            if p['proposalId'] == proposal_id:
                proposal = p
                break
        
        if not proposal or proposal['status'] != 'approved':
            return False
        
        # Parse change details
        change_details = json.loads(proposal['changeDetails'])
        target_sheet = proposal['targetSheet']
        
        # Apply changes based on target sheet
        if target_sheet == 'Canonical_Schema':
            success = self._apply_canonical_changes(change_details)
        elif target_sheet == 'MP_Mapping':
            success = self._apply_mapping_changes(change_details)
        elif target_sheet == 'Attribute_Dictionary':
            success = self._apply_dictionary_changes(change_details)
        else:
            return False
        
        if success:
            proposal['appliedAt'] = datetime.now().isoformat()
            self._save_proposals()
        
        return success
    
    def _apply_canonical_changes(self, changes: Dict[str, Any]) -> bool:
        """Apply changes to Canonical_Schema."""
        # Implementation would update the actual CSV file
        print(f"Applying Canonical_Schema changes: {changes}")
        return True
    
    def _apply_mapping_changes(self, changes: Dict[str, Any]) -> bool:
        """Apply changes to MP_Mapping."""
        print(f"Applying MP_Mapping changes: {changes}")
        return True
    
    def _apply_dictionary_changes(self, changes: Dict[str, Any]) -> bool:
        """Apply changes to Attribute_Dictionary."""
        print(f"Applying Attribute_Dictionary changes: {changes}")
        return True
    
    def _save_proposals(self):
        """Save proposals to CSV."""
        if not self.proposals:
            return
        
        # Ensure directory exists
        self.approval_sheet_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.approval_sheet_path, 'w', encoding='utf-8', newline='') as f:
            fieldnames = [
                'proposalId', 'targetSheet', 'changeType', 'changeDetails',
                'proposer', 'proposedAt', 'reviewer', 'status',
                'reviewedAt', 'reviewNotes', 'appliedAt'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.proposals)
    
    def get_pending_proposals(self) -> List[Dict[str, Any]]:
        """Get all pending proposals."""
        return [p for p in self.proposals if p['status'] == 'pending']
    
    def get_proposal_stats(self) -> Dict[str, int]:
        """Get proposal statistics."""
        stats = {
            'total': len(self.proposals),
            'pending': 0,
            'approved': 0,
            'rejected': 0,
            'applied': 0
        }

        for proposal in self.proposals:
            status = proposal['status']
            if status in stats:
                stats[status] += 1

            if proposal['appliedAt']:
                stats['applied'] += 1

        return stats

    def get_determination_review_alerts(self) -> List[Dict[str, Any]]:
        """Get alerts for determinations that need review (document_updated)."""
        try:
            from change_monitor import ChangeMonitor
            monitor_dir = self.approval_sheet_path.parent.parent / "20_QA" / "monitoring"
            monitor = ChangeMonitor(monitor_dir)
            return monitor.get_determination_review_alerts()
        except Exception:
            return []

def main():
    """Demo the approval workflow."""
    approval_path = Path(__file__).parent.parent / '02_Templates' / 'Approval_Sheet.csv'
    workflow = ApprovalWorkflow(approval_path)
    
    # Create a sample proposal
    change_details = {
        'attributeId': 'size',
        'attributeName_ja': 'サイズ',
        'attributeName_en': 'Size',
        'definition': 'Product size specification',
        'dataType': 'string',
        'allowedValues': 'S;M;L;XL;XXL',
        'requiredFlag': True
    }
    
    proposal_id = workflow.create_proposal(
        target_sheet='Canonical_Schema',
        change_type='add',
        change_details=change_details,
        proposer='ops_team'
    )
    
    print(f"Created proposal: {proposal_id}")
    
    # Review the proposal
    workflow.review_proposal(
        proposal_id=proposal_id,
        reviewer='lead_reviewer',
        status='approved',
        review_notes='Looks good, standard size values'
    )
    
    print("Proposal approved")
    
    # Apply the proposal
    workflow.apply_proposal(proposal_id)
    print("Proposal applied")
    
    # Show stats
    stats = workflow.get_proposal_stats()
    print(f"\nProposal stats: {stats}")

if __name__ == '__main__':
    main()





