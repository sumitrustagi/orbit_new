"""Authentication forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(min=2, max=64)],
        render_kw={"placeholder": "Username or email", "autofocus": True},
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired()],
        render_kw={"placeholder": "Password"},
    )
    remember_me = BooleanField("Remember me")
    submit = SubmitField("Sign In")
