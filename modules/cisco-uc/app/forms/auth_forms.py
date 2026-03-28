"""Authentication forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=2, max=80)])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit   = SubmitField("Sign In")


class SetupForm(FlaskForm):
    username   = StringField("Admin Username", validators=[DataRequired(), Length(min=2, max=80)])
    email      = StringField("Admin Email", validators=[DataRequired(), Length(max=254)])
    password   = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    app_name   = StringField("Application Name", default="Cisco UC Hub")
    cucm_host  = StringField("CUCM Host")
    cucm_user  = StringField("CUCM Username")
    cucm_pass  = PasswordField("CUCM Password")
    submit     = SubmitField("Complete Setup")
