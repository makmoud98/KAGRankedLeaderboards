from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from setup_database import Base, User

engine = create_engine('sqlite:///ranks.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()
email = raw_input('enter new admin email: ')
print('looking for %s in the database' % email)
user = session.query(User).filter_by(email=email).first()
if user is None:
    print('%s was not found..' % email)
    print('please login on the website at least once before promoting')
else:
    print('%s was found..' % email)
    print('promoting %s to admin..' % email)
    user.admin = True
    session.commit()
    session.close()
