from sqlmodel import SQLModel


############# TOKEN ##################
class Token(SQLModel):
    access_token: str
    token_type: str