"""CUCM-related forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class PhoneSearchForm(FlaskForm):
    search_field = SelectField("Search By", choices=[
        ("name", "Device Name"),
        ("description", "Description"),
        ("directory_number", "Directory Number"),
        ("device_pool", "Device Pool"),
    ])
    search_value = StringField("Search Value", validators=[Optional(), Length(max=128)])
    submit       = SubmitField("Search")


class PhoneForm(FlaskForm):
    name              = StringField("Device Name", validators=[DataRequired(), Length(max=128)])
    description       = StringField("Description", validators=[Optional(), Length(max=300)])
    model             = StringField("Model", validators=[Optional(), Length(max=80)])
    protocol          = SelectField("Protocol", choices=[("SIP", "SIP"), ("SCCP", "SCCP")])
    device_pool       = StringField("Device Pool", validators=[Optional(), Length(max=128)])
    calling_search_space = StringField("Calling Search Space", validators=[Optional(), Length(max=128)])
    directory_number  = StringField("Directory Number", validators=[Optional(), Length(max=30)])
    location          = StringField("Location", validators=[Optional(), Length(max=128)])
    owner_user_id     = StringField("Owner User ID", validators=[Optional(), Length(max=128)])
    submit            = SubmitField("Save")
