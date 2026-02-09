from Backend.extensions import db
from datetime import datetime, timezone


class User(db.Model):
    __tablename__ = "auth_user"  # mirror Django table name if needed

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(150))
    last_name = db.Column(db.String(150))
    is_active = db.Column(db.Boolean, default=True)
    is_staff = db.Column(db.Boolean, default=False)
    is_superuser = db.Column(db.Boolean, default=False)
    date_joined = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<User {self.username}>"


class Candidate(db.Model):
    __tablename__ = "candidatemanagapp_candidate"

    id = db.Column(db.Integer, primary_key=True)

    # One-to-One with User
    user_id = db.Column(db.Integer, db.ForeignKey("auth_user.id"), unique=True, nullable=True)
    user = db.relationship("User", backref="Candidates", uselist=False)  # one-to-one

    phone = db.Column(db.String(522), nullable=False)
    academic_field = db.Column(db.String(522), nullable=False)
    institution = db.Column(db.String(522), nullable=False)
    program_interest = db.Column(db.String(522), nullable=False)
    summary = db.Column(db.Text, nullable=True)

    profile_filled = db.Column(db.Boolean, default=False)
    cv_filled = db.Column(db.Boolean, default=False)
    bot_scre_filled = db.Column(db.Boolean, default=False)
    bot_scre_generated = db.Column(db.Boolean, default=False)
    bot_scre_passed = db.Column(db.Boolean, default=False)

    bot_domain_selected = db.Column(db.String(522))
    bot_obt_score = db.Column(db.Numeric(10, 2), nullable=True)
    bot_tot_score = db.Column(db.Numeric(10, 2), nullable=True)
    bot_obt_perc = db.Column(db.String(200))

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=True
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True
    )

    def __repr__(self):
        return f"<Candidate {self.id} - {self.phone}>"

class CandidateResearch(db.Model):
    __tablename__ = "candidatemanagapp_candidateresearch"

    id = db.Column(db.Integer, primary_key=True)

    # ForeignKey and relationship to Candidate
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidatemanagapp_candidate.id"), nullable=False)
    candidate = db.relationship("Candidate", backref="Candidate_researches")
    title = db.Column(db.String(255))
    journal = db.Column(db.String(255))
    year = db.Column(db.Integer)
    file = db.Column(db.String(500))
    description = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

 
  

class CandidateEvalAI(db.Model):
    __tablename__ = "candidatemanagapp_candidateevalai"    

    id = db.Column(db.Integer, primary_key=True)

    # Django OneToOneField → FK + unique
    candidate_id = db.Column(
        db.Integer,
        db.ForeignKey("candidatemanagapp_candidate.id"),
        unique=True,
        nullable=True
    )
    candidate = db.relationship("Candidate", backref="Candidates_eval_ai")

    to_pickup = db.Column(db.Boolean, default=False)
    picked_up = db.Column(db.Boolean, default=False)
    completed = db.Column(db.Boolean, default=False)
    candidate_attempted = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    ) 
    evaluation_picked_up  =  db.Column(db.Boolean, default=False)
    evaluation_progress_error_occured  =  db.Column(db.Boolean, default=False)
    evaluation_completed =  db.Column(db.Boolean, default=False) 
    candidate_passed = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    ) 
    obt_score = db.Column(
        db.Numeric(10, 2),
        nullable=True
    ) 
    tot_score = db.Column(
        db.Numeric(10, 2),
        nullable=True
    ) 
    obt_perc = db.Column(
        db.String(200),
        nullable=True
    ) 
    progress_error_occured = db.Column(db.Boolean, default=False) 
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    ) 
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


class CandidateQuizQuestion(db.Model):
    __tablename__ = "candidatemanagapp_candidatequizquestion"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("candidatemanagapp_candidateevalai.id"), nullable=False)
    quiz = db.relationship("CandidateEvalAI", backref="questions") 
    question_text = db.Column(db.Text)
    answer_text = db.Column(db.Text)
    options = db.Column(db.Text, nullable=True)
    correct_answer = db.Column(db.String(50), nullable=True) 
    user_answer = db.Column(db.Text, nullable=True) 
    its_score = db.Column(
        db.Numeric(10, 2),   # max_digits=10, decimal_places=2
        nullable=True
    )
    explanation_text = db.Column(db.Text)
    question_type = db.Column(db.String(50))
    source_pdf = db.Column(db.String(255))

