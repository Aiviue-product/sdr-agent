"""
FateMatrix ORM Model
SQLAlchemy model representing the 'fate_matrix' table in the database.
This is the source of truth for the fate_matrix table schema.

FATE = Frustration, Aspiration, Target solution, Evidence
This table stores persona-specific pain points and messaging guidelines
for personalized email generation.

IMPORTANT: This model matches the actual Supabase database schema exactly.
"""
from sqlalchemy import Column, BigInteger, Text, DateTime, UniqueConstraint
from app.shared.db.base import Base


class FateMatrix(Base):
    """
    ORM Model for the fate_matrix table.
    
    FATE Framework:
    - F (Frustration/Pain): What frustrates this persona?
    - A (Aspiration/Goal): What do they want to achieve?
    - T (Target Solution): How our solution helps them
    - E (Evidence): Proof/credibility we can offer
    
    Used by the email generation service to create personalized emails
    based on sector + designation combinations.
    """
    __tablename__ = "fate_matrix"

    # Primary Key
    id = Column(BigInteger, primary_key=True)
    
    # Targeting (sector + role combination) - has unique constraint in DB
    sector = Column(Text, nullable=False)
    designation_role = Column(Text, nullable=False)
    
    # FATE Framework Components
    f_pain = Column(Text, nullable=False)        # Frustration/Pain points
    a_goal = Column(Text, nullable=False)        # Aspiration/Goal
    t_solution = Column(Text, nullable=False)    # Target solution
    e_evidence = Column(Text, nullable=False)    # Evidence/Social proof
    
    # Additional context
    urgency_level = Column(Text, nullable=True)  # Optional urgency indicator
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), nullable=True)

    # Unique constraint on sector + designation_role (exists in DB)
    __table_args__ = (
        UniqueConstraint('sector', 'designation_role', name='fate_matrix_sector_designation_role_key'),
    )

    def __repr__(self):
        return f"<FateMatrix(id={self.id}, sector='{self.sector}', role='{self.designation_role}')>"
