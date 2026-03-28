"""Settings forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional, Length


class GeneralSettingsForm(FlaskForm):
    app_name       = StringField("Application Name", validators=[DataRequired(), Length(max=64)])
    primary_color  = StringField("Primary Color", validators=[DataRequired()])
    accent_color   = StringField("Accent Color", validators=[DataRequired()])
    submit         = SubmitField("Save")


class GraphSettingsForm(FlaskForm):
    tenant_id      = StringField("Tenant ID", validators=[DataRequired()])
    client_id      = StringField("Client ID", validators=[DataRequired()])
    client_secret  = StringField("Client Secret", validators=[DataRequired()])
    submit         = SubmitField("Save Graph Settings")


class EmailSettingsForm(FlaskForm):
    smtp_host      = StringField("SMTP Host", validators=[Optional()])
    smtp_port      = StringField("SMTP Port", validators=[Optional()])
    smtp_username  = StringField("SMTP Username", validators=[Optional()])
    smtp_password  = StringField("SMTP Password", validators=[Optional()])
    smtp_sender    = StringField("Sender Email", validators=[Optional()])
    smtp_use_tls   = BooleanField("Use TLS", default=True)
    submit         = SubmitField("Save Email Settings")


class SecuritySettingsForm(FlaskForm):
    session_timeout    = StringField("Session Timeout (minutes)", validators=[Optional()])
    max_login_attempts = StringField("Max Login Attempts", validators=[Optional()])
    lockout_duration   = StringField("Lockout Duration (minutes)", validators=[Optional()])
    submit             = SubmitField("Save Security Settings")
