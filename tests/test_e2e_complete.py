import os
os.environ['TESTING'] = 'true'
import pytest
import urllib.parse
from app import create_app
from database.repositories import article_repository, user_repository, saved_article_repository
from auth.authentication import AuthManager

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key-123'
    with app.test_client() as client:
        yield client

def test_article_detail_resolution_all_articles_in_db(client):
    """Verify that every single article currently in the database can be loaded via ID and Title without 404 or redirect."""
    with client.session_transaction() as sess:
        sess['user_id'] = '666666666666666666666666'
        sess['username'] = 'testadmin'
        sess['is_admin'] = True

    articles = article_repository.get_all(limit=0)
    assert len(articles) > 0, "Database should have scraped articles"

    for art in articles:
        art_id = str(art.get('_id', ''))
        title = art.get('title', '')
        
        # 1. Test resolution via ObjectId (The primary URL scheme used by the UI)
        resp_id = client.get(f'/article/{art_id}')
        assert resp_id.status_code == 200, f"Failed to load article by ID: {art_id} - {title}"

        # 2. Test direct repository resolution by title
        doc_by_title = article_repository.get_article(title)
        assert doc_by_title is not None, f"Failed repo lookup for title: {title}"

        # 3. Test HTTP Title route when title does not contain double slash URL collapsing characters
        if '//' not in title and '\n' not in title:
            quoted_title = urllib.parse.quote(title, safe='')
            resp_title = client.get(f'/article/{quoted_title}')
            assert resp_title.status_code == 200, f"Failed to load article by Title: {title}"

def test_specific_user_reported_articles(client):
    """Specifically test the 2 articles reported in the user screenshot."""
    with client.session_transaction() as sess:
        sess['user_id'] = '666666666666666666666666'
        sess['username'] = 'testadmin'
        sess['is_admin'] = True

    # 1. BOL News with en-dash
    bol_title = "BOL News – Latest News, Politics, Sports and Entertainment"
    art1 = article_repository.get_article(bol_title)
    if art1:
        resp1 = client.get(f'/article/{art1["_id"]}')
        assert resp1.status_code == 200
        resp1_title = client.get(f'/article/{urllib.parse.quote(bol_title)}')
        assert resp1_title.status_code == 200

    # 2. Tricore frontend
    tri_title = "Dependable equipment for the people who deliver care."
    art2 = article_repository.get_article(tri_title)
    if art2:
        resp2 = client.get(f'/article/{art2["_id"]}')
        assert resp2.status_code == 200

def test_nonexistent_article_returns_404(client):
    """Verify that a genuine nonexistent article returns status code 404 with error template."""
    with client.session_transaction() as sess:
        sess['user_id'] = '666666666666666666666666'
        sess['username'] = 'testadmin'
        sess['is_admin'] = True

    resp = client.get('/article/completely-nonexistent-article-id-99999999')
    assert resp.status_code == 404
    assert b"Article Not Found" in resp.data

def test_user_registration_and_login_flow(client):
    """Test comprehensive user registration validations and login with username or email."""
    import uuid
    uid = str(uuid.uuid4())[:8]
    test_user = f"qa_user_{uid}"
    test_email = f"qa_{uid}@example.com"
    test_pwd = "Password123!"

    # 1. Registration validation - password mismatch
    resp = client.post('/register', data={
        'fullname': 'QA Tester',
        'email': test_email,
        'username': test_user,
        'password': test_pwd,
        'confirm_password': 'DifferentPassword'
    }, follow_redirects=True)
    assert b"Passwords do not match" in resp.data

    # 2. Registration validation - short password
    resp = client.post('/register', data={
        'fullname': 'QA Tester',
        'email': test_email,
        'username': test_user,
        'password': '123',
        'confirm_password': '123'
    }, follow_redirects=True)
    assert b"Password must be at least 6 characters" in resp.data

    # 3. Successful Registration
    resp = client.post('/register', data={
        'fullname': 'QA Tester',
        'email': test_email,
        'username': test_user,
        'password': test_pwd,
        'confirm_password': test_pwd
    }, follow_redirects=True)
    assert resp.status_code == 200

    # Approve the newly created user for login testing
    db_user = user_repository.get_user_by_username(test_user)
    assert db_user is not None
    user_repository.approve_user(db_user['_id'])

    # 4. Duplicate username check
    resp_dup = client.post('/register', data={
        'fullname': 'Another User',
        'email': f"other_{uid}@example.com",
        'username': test_user,
        'password': test_pwd,
        'confirm_password': test_pwd
    }, follow_redirects=True)
    assert b"Username is already taken" in resp_dup.data

    # 5. Duplicate email check
    resp_dup_email = client.post('/register', data={
        'fullname': 'Another User',
        'email': test_email,
        'username': f"diff_user_{uid}",
        'password': test_pwd,
        'confirm_password': test_pwd
    }, follow_redirects=True)
    assert b"account with this email already exists" in resp_dup_email.data

    # 6. Login via Username
    client.get('/logout')
    resp_login_user = client.post('/login', data={
        'username': test_user,
        'password': test_pwd
    }, follow_redirects=True)
    assert resp_login_user.status_code == 200
    assert b"Welcome back" in resp_login_user.data

    # 7. Login via Email
    client.get('/logout')
    resp_login_email = client.post('/login', data={
        'username': test_email,
        'password': test_pwd
    }, follow_redirects=True)
    assert resp_login_email.status_code == 200
    assert b"Welcome back" in resp_login_email.data

def test_saved_articles_bookmarking(client):
    """Test saving and unsaving bookmarks."""
    with client.session_transaction() as sess:
        sess['user_id'] = '666666666666666666666666'
        sess['username'] = 'testadmin'
        sess['is_admin'] = True

    articles = article_repository.get_all(limit=2)
    assert len(articles) > 0
    test_title = articles[0]['title']

    # Save
    save_resp = client.post('/api/articles/save', json={'title': test_title})
    assert save_resp.status_code == 200
    assert save_resp.json['success'] is True

    # View Saved Page
    saved_page = client.get('/saved')
    assert saved_page.status_code == 200
    assert test_title.encode('utf-8')[:30] in saved_page.data

    # Unsave
    unsave_resp = client.post('/api/articles/unsave', json={'title': test_title})
    assert unsave_resp.status_code == 200
    assert unsave_resp.json['success'] is True

def test_admin_article_crud(client):
    """Test creating, editing, and deleting an article via Admin operations."""
    with client.session_transaction() as sess:
        sess['user_id'] = '666666666666666666666666'
        sess['username'] = 'testadmin'
        sess['is_admin'] = True

    unique_title = "Global AI Summit 2026 Concludes in Geneva with Major Ethics Accords"
    sample_body = "Delegates from over 90 countries today finalized a landmark treaty on AI transparency and safety protocols."

    # 1. Create Article via Admin
    resp_new = client.post('/admin/article/new', data={
        'title': unique_title,
        'body': sample_body,
        'language': 'English',
        'source_url': 'https://ai-summit-news.org/articles/2026',
        'publication_date': '2026-08-28'
    }, follow_redirects=True)
    assert resp_new.status_code == 200

    # Verify created
    art = article_repository.get_article(unique_title)
    assert art is not None
    art_id = art['_id']

    # 2. View Created Article
    resp_view = client.get(f'/article/{art_id}')
    assert resp_view.status_code == 200
    assert b"Global AI Summit" in resp_view.data

    # 3. Edit Article
    updated_title = "Global AI Summit 2026 Concludes in Geneva - Updated Treaty Text"
    resp_edit = client.post(f'/admin/article/edit/{art_id}', data={
        'title': updated_title,
        'body': sample_body + " Full text signed.",
        'language': 'English',
        'source_url': 'https://ai-summit-news.org/articles/2026',
        'publication_date': '2026-08-28'
    }, follow_redirects=True)
    assert resp_edit.status_code == 200

    art_updated = article_repository.get_article(art_id)
    assert art_updated['title'] == updated_title

    # 4. Delete Article
    resp_del = client.post(f'/admin/article/delete/{art_id}', follow_redirects=True)
    assert resp_del.status_code == 200

    assert article_repository.get_article(art_id) is None

def test_admin_user_management(client):
    """Test promoting, demoting, toggling approval status, and deleting users via Admin panel."""
    with client.session_transaction() as sess:
        sess['user_id'] = '666666666666666666666666'
        sess['username'] = 'testadmin'
        sess['is_admin'] = True

    import uuid
    uid = str(uuid.uuid4())[:8]
    test_u = f"managed_user_{uid}"
    
    # Create test user
    pwd_hash, salt = AuthManager.hash_password("Pass1234!")
    coll = user_repository.collection
    insert_res = coll.insert_one({
        'username': test_u,
        'fullname': 'Managed User',
        'email': f"{test_u}@example.com",
        'password_hash': pwd_hash,
        'salt': salt,
        'approved': False,
        'is_admin': False
    })
    target_user_id = str(insert_res.inserted_id)

    # 1. Approve User
    resp_appr = client.post(f'/admin/approve/{target_user_id}', follow_redirects=True)
    assert resp_appr.status_code == 200
    u_data = user_repository.get_user_by_id(target_user_id)
    assert u_data['approved'] is True

    # 2. Promote to Admin
    resp_role = client.post(f'/admin/users/role/{target_user_id}', data={'is_admin': 'true'}, follow_redirects=True)
    assert resp_role.status_code == 200
    u_data = user_repository.get_user_by_id(target_user_id)
    assert u_data['is_admin'] is True

    # 3. Deactivate User
    resp_stat = client.post(f'/admin/users/status/{target_user_id}', data={'approved': 'false'}, follow_redirects=True)
    assert resp_stat.status_code == 200
    u_data = user_repository.get_user_by_id(target_user_id)
    assert u_data['approved'] is False

    # 4. Delete User
    resp_del_user = client.post(f'/admin/users/delete/{target_user_id}', follow_redirects=True)
    assert resp_del_user.status_code == 200
    assert user_repository.get_user_by_id(target_user_id) is None

def test_multilingual_routes_and_views(client):
    """Test languages page, Arabic and Russian filtered explorers, and analytics view."""
    with client.session_transaction() as sess:
        sess['user_id'] = '666666666666666666666666'
        sess['username'] = 'testadmin'
        sess['is_admin'] = True

    # 1. Languages view
    resp_lang = client.get('/languages')
    assert resp_lang.status_code == 200
    assert b"Multilingual Analysis" in resp_lang.data
    assert b"Arabic" in resp_lang.data
    assert b"Russian" in resp_lang.data

    # 2. Arabic explorer
    resp_ar = client.get('/explorer?lang=Arabic')
    assert resp_ar.status_code == 200

    # 3. Russian explorer
    resp_ru = client.get('/explorer?lang=Russian')
    assert resp_ru.status_code == 200

    # 4. Analytics view
    resp_an = client.get('/analytics')
    assert resp_an.status_code == 200
    assert b"articleVolumeChart" in resp_an.data

def test_profile_and_settings_persistence(client):
    """Test updating user profile and application settings."""
    # Create and login as a new user
    import uuid
    uid = str(uuid.uuid4())[:8]
    test_u = f"prof_user_{uid}"
    pwd_hash, salt = AuthManager.hash_password("Pass1234!")
    coll = user_repository.collection
    insert_res = coll.insert_one({
        'username': test_u,
        'fullname': 'Original Name',
        'email': f"{test_u}@example.com",
        'password_hash': pwd_hash,
        'salt': salt,
        'approved': True,
        'is_admin': False
    })
    target_user_id = str(insert_res.inserted_id)

    with client.session_transaction() as sess:
        sess['user_id'] = target_user_id
        sess['username'] = test_u
        sess['is_admin'] = False

    # 1. View Profile
    resp_prof_view = client.get('/profile')
    assert resp_prof_view.status_code == 200
    assert b"Original Name" in resp_prof_view.data

    # 2. Update Profile
    resp_prof_update = client.post('/profile', data={
        'fullname': 'Updated Fullname',
        'email': f"updated_{test_u}@example.com",
        'password': 'NewPassword123!',
        'confirm_password': 'NewPassword123!'
    }, follow_redirects=True)
    assert resp_prof_update.status_code == 200
    assert b"Profile updated successfully" in resp_prof_update.data

    # Verify DB update
    updated_doc = user_repository.get_user_by_id(target_user_id)
    assert updated_doc['fullname'] == 'Updated Fullname'
    assert updated_doc['email'] == f"updated_{test_u}@example.com"
    assert AuthManager.verify_password(updated_doc['password_hash'], updated_doc['salt'], 'NewPassword123!')

    # 3. Standard user blocked from Settings
    resp_settings_blocked = client.get('/settings')
    assert resp_settings_blocked.status_code == 302

    # 4. Admin can access and update Settings
    with client.session_transaction() as sess:
        sess['is_admin'] = True

    resp_settings = client.post('/settings', data={
        'theme': 'light',
        'language': 'en',
        'rate_limit': '2000',
        'notify_scrape': 'on'
    }, follow_redirects=True)
    assert resp_settings.status_code == 200
    assert b"Settings updated successfully" in resp_settings.data

    # Clean up user
    user_repository.delete_user(target_user_id)

