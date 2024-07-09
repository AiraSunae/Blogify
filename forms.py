from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditorField


class CreatePostForm(FlaskForm):
    title = StringField("Blog Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    image = StringField("Image URL", validators=[DataRequired(), URL()])
    content = CKEditorField("Content Section", validators=[DataRequired()])
    submit = SubmitField("Create! ")


class RegisterForm(FlaskForm):
    address = StringField("Address", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired()])
    register = SubmitField("Register!")


class LoginForm(FlaskForm):
    address = StringField("Address", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    register = SubmitField("Login!")

class CommentForm(FlaskForm):
    content = CKEditorField("Comment", validators=[DataRequired()])
    submit = SubmitField("Post! ")
