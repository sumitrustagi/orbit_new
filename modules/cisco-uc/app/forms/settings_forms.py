"""Settings forms for configuring Cisco integrations."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class CUCMSettingsForm(FlaskForm):
    cucm_host       = StringField("CUCM Host", validators=[DataRequired(), Length(max=200)])
    cucm_username   = StringField("Username", validators=[DataRequired(), Length(max=128)])
    cucm_password   = PasswordField("Password", validators=[Optional()])
    cucm_version    = SelectField("AXL Version", choices=[
        ("14.0", "14.0"), ("12.5", "12.5"), ("12.0", "12.0"),
        ("11.5", "11.5"), ("11.0", "11.0"), ("10.5", "10.5"),
    ])
    cucm_verify_ssl = BooleanField("Verify SSL")
    submit          = SubmitField("Save CUCM Settings")


class UnitySettingsForm(FlaskForm):
    unity_host       = StringField("Unity Host", validators=[DataRequired(), Length(max=200)])
    unity_username   = StringField("Username", validators=[DataRequired(), Length(max=128)])
    unity_password   = PasswordField("Password", validators=[Optional()])
    unity_verify_ssl = BooleanField("Verify SSL")
    submit           = SubmitField("Save Unity Settings")


class IMPSettingsForm(FlaskForm):
    imp_host       = StringField("IM&P Host", validators=[DataRequired(), Length(max=200)])
    imp_username   = StringField("Username", validators=[DataRequired(), Length(max=128)])
    imp_password   = PasswordField("Password", validators=[Optional()])
    imp_verify_ssl = BooleanField("Verify SSL")
    submit         = SubmitField("Save IM&P Settings")


class ExpresswaySettingsForm(FlaskForm):
    expressway_host       = StringField("Expressway Host", validators=[DataRequired(), Length(max=200)])
    expressway_username   = StringField("Username", validators=[DataRequired(), Length(max=128)])
    expressway_password   = PasswordField("Password", validators=[Optional()])
    expressway_verify_ssl = BooleanField("Verify SSL")
    submit                = SubmitField("Save Expressway Settings")


class GeneralSettingsForm(FlaskForm):
    app_name    = StringField("Application Name", validators=[DataRequired(), Length(max=80)])
    session_timeout = IntegerField("Session Timeout (minutes)", default=30)
    submit      = SubmitField("Save General Settings")


class EmailSettingsForm(FlaskForm):
    smtp_host     = StringField("SMTP Host", validators=[Optional(), Length(max=200)])
    smtp_port     = IntegerField("SMTP Port", default=587)
    smtp_username = StringField("SMTP Username", validators=[Optional(), Length(max=128)])
    smtp_password = PasswordField("SMTP Password", validators=[Optional()])
    smtp_use_tls  = BooleanField("Use TLS", default=True)
    smtp_sender   = StringField("Sender Email", validators=[Optional(), Length(max=254)])
    submit        = SubmitField("Save Email Settings")


class SecuritySettingsForm(FlaskForm):
    password_min_length   = IntegerField("Min Password Length", default=8)
    password_require_upper = BooleanField("Require Uppercase", default=True)
    password_require_digit = BooleanField("Require Digit", default=True)
    password_require_special = BooleanField("Require Special Char", default=True)
    max_login_attempts    = IntegerField("Max Login Attempts", default=5)
    lockout_duration      = IntegerField("Lockout Duration (minutes)", default=15)
    submit                = SubmitField("Save Security Settings")
