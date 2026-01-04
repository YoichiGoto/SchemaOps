#!/usr/bin/env python3
"""
Approval workflow automation for schema changes.
Manages proposal creation, review, and application process.
"""
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class ApprovalWorkflow:
    def __init__(self, approval_sheet_path: Path):
        self.approval_sheet_path = approval_sheet_path
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
                       status: str, review_notes: str = '') -> bool:
        """Review a proposal (approve/reject)."""
        for proposal in self.proposals:
            if proposal['proposalId'] == proposal_id:
                proposal['reviewer'] = reviewer
                proposal['status'] = status
                proposal['reviewedAt'] = datetime.now().isoformat()
                proposal['reviewNotes'] = review_notes
                
                self._save_proposals()
                return True
        
        return False
    
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





