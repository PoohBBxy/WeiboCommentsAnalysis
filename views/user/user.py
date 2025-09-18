import os
import time
import random

from flask import Flask, session, render_template, redirect, Blueprint, request, flash, url_for, jsonify
from werkzeug.utils import secure_filename
from utils.query import query
from werkzeug.security import check_password_hash, generate_password_hash
import re

from itsdangerous import SignatureExpired, BadTimeSignature
from extensions import mail
from flask_mail import Message

from .utils import get_current_user_info, get_serializer

ub = Blueprint('user', __name__, url_prefix="/user", template_folder='templates')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
UPLOAD_FOLDER = 'static/avatars'
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename): return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _push_ban_notice(reason, details):
    session['ban_notice'] = {
        'title': '账户已被禁用',
        'reason': reason or '管理员未提供具体原因。',
        'details': details or '如需恢复访问，请点击“申诉”按钮向平台提交申请，我们将在 1-2 个工作日内答复。',
        'appeal_url': 'mailto:wang88776@foxmail.com?subject=账户申诉&body=请描述您的账户信息与申诉理由'
    }


def _pop_ban_notice():
    return session.pop('ban_notice', None)

@ub.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('auth_portal.html', page_mode='login', prefill=None, ban_notice=_pop_ban_notice())
    else:
        login_identifier = request.form.get('login_identifier', '').strip()
        password = request.form.get('password', '').strip()
        if not login_identifier or not password:
            flash("⚠️ 用户名/邮箱和密码不能为空！", category="warning")
            return redirect('/user/login')

        # [V3] 查询用户时一并获取封禁原因
        users = query(
            'SELECT username, password, status, ban_reason, ban_details FROM user WHERE username = %s OR email = %s LIMIT 1',
            [login_identifier, login_identifier],
            'select'
        )
        if not users:
            flash("❌ 登录失败：该用户不存在", category="error")
            return redirect('/user/login')

        username, db_password, status, ban_reason, ban_details = users[0]

        if not check_password_hash(db_password, password):
            flash("❌ 登录失败：用户名/邮箱或密码错误", category="error")
            return redirect('/user/login')

        # [V3] 显示详细的封禁提示
        if status == 'disabled':
            _push_ban_notice(ban_reason, ban_details)
            flash('账户访问受限||您的账户已被禁用，请点击申诉按钮或联系管理员。', 'error')
            return redirect('/user/login')

        session['username'] = username
        flash('登录成功||欢迎回来，{}！'.format(username), 'success')
        return redirect('/page/home')


@ub.route('/register', methods=['GET', 'POST'])
def register():
    ban_notice = _pop_ban_notice()
    if request.method == 'GET':
        return render_template('register_portal.html',
                               prefill={},
                               ban_notice=ban_notice
        )
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    check_password = request.form.get('checkPassword', '').strip()
    nickname = request.form.get('nickname', '').strip()
    email = request.form.get('email', '').strip()
    verification_code = request.form.get('verification_code', '').strip()
    form_data = {
        'username': username,
        'nickname': nickname,
        'email': email
    }
    if not all([username, password, check_password, email]):
        flash("⚠️ 带*的必填项（用户名、邮箱、密码）不能为空！", category="warning")
        return render_template(
            'register_portal.html',
            prefill=form_data,
            ban_notice=ban_notice
        )
    stored_code_info = session.get('verification_code')
    if not stored_code_info or stored_code_info.get('code') != verification_code or stored_code_info.get('email') != email:
        flash("❌ 注册失败！原因：邮箱验证码错误或已过期。", category="error")
        return render_template(
            'register_portal.html',
            prefill=form_data,
            ban_notice=ban_notice
        )
    if time.time() - stored_code_info.get('timestamp', 0) > 300:
        flash("❌ 注册失败！原因：邮箱验证码已过期，请重新获取。",
              category="error"
              )
        return render_template(
            'register_portal.html',
            prefill=form_data,
            ban_notice=ban_notice
        )
    if password != check_password:
        flash("❌ 注册失败！原因：两次输入的密码不一致", category="error")
        return render_template(
            'register_portal.html',
            prefill=form_data,
            ban_notice=ban_notice
        )
    if len(password) < 8 or not re.search(r'\d', password) or not re.search(r'[A-Za-z]', password):
        flash("⚠️ 密码强度不足（至少 8 位，包含字母和数字）", category="warning")
        return render_template(
            'register_portal.html',
            prefill=form_data,
            ban_notice=ban_notice
        )
    users_count = query(
        'SELECT count(*) FROM user WHERE username = %s',
        [username],
        'select'
    )
    if users_count and users_count[0][0] > 0:
        flash("❌ 注册失败！原因：该用户名已被注册", category="error")
        return render_template(
            'register_portal.html',
            prefill=form_data,
            ban_notice=ban_notice
        )
    email_count = query('SELECT count(*) FROM user WHERE email = %s', [email], 'select')
    if email_count and email_count[0][0] > 0: flash("❌ 注册失败！原因：该电子邮箱已被使用", category="error"); return render_template('register_portal.html', prefill=form_data, ban_notice=ban_notice)
    session.pop('verification_code', None); hashed_password = generate_password_hash(password, method='pbkdf2:sha256'); create_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    query("INSERT INTO user(username, password, nickname, email, createTime, role) VALUES(%s, %s, %s, %s, %s, %s)", [username, hashed_password, nickname, email, create_time_str, 'user'])
    flash("注册成功||请使用新账号登录 😊", category="success"); return redirect('/user/login')
@ub.route('/logout')
def logout(): session.pop('username', None); flash("您已退出登录", category="info"); return redirect('/user/login')
@ub.route('/profile', methods=['GET'])
def profile_page():
    username = session.get('username')
    if not username: flash("请先登录", "warning"); return redirect('/user/login')
    current_user = get_current_user_info(username)
    if not current_user: flash("无法获取用户信息，请重新登录", "error"); session.pop('username', None); return redirect('/user/login')
    return render_template('profile.html', current_user=current_user, username=current_user['username'], nickname=current_user['nickname'] or current_user['username'], user_role=current_user['role'], avatar_url=current_user['avatar_url'], active_page='profile')
@ub.route('/profile/update', methods=['POST'])
def update_profile():
    username = session.get('username')
    if not username: flash("会话已过期，请重新登录", "warning"); return redirect('/user/login')
    current_user = get_current_user_info(username)
    if not current_user: flash("无法获取用户信息，请重新登录", "error"); return redirect('/user/login')
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    original_email = current_user.get('email'); nickname = request.form.get('nickname', '').strip(); new_email = request.form.get('email', '').strip()
    query("UPDATE user SET nickname = %s WHERE username = %s", [nickname, username])

    avatar_updated = False
    avatar_url_value = None
    if 'avatar' in request.files:
        file = request.files['avatar']
        if file and file.filename != '':
            if not allowed_file(file.filename):
                if is_ajax:
                    return jsonify({'success': False, 'message': '不支持的头像文件类型'}), 400
                flash('不支持的头像文件类型', 'error'); return redirect(url_for('user.profile_page'))
            # enforce 5MB avatar limit
            try:
                pos = file.stream.tell()
            except Exception:
                pos = 0
            try:
                file.stream.seek(0, os.SEEK_END)
                size = file.stream.tell()
            finally:
                file.stream.seek(pos)
            if size > 5 * 1024 * 1024:
                if is_ajax:
                    return jsonify({'success': False, 'message': '头像大小不能超过 5MB'}), 400
                flash('头像大小不能超过 5MB', 'error'); return redirect(url_for('user.profile_page'))

            timestamp = int(time.time()); filename = secure_filename(f"{username}_{timestamp}_{file.filename}"); filepath = os.path.join(UPLOAD_FOLDER, filename); file.save(filepath); db_path = os.path.join('avatars', filename).replace('\\', '/'); query("UPDATE user SET avatar = %s WHERE username = %s", [db_path, username])
            avatar_updated = True
            avatar_url_value = db_path

    if new_email and new_email != original_email:
        verification_code = request.form.get('verification_code', ''); stored_code_info = session.get('verification_code'); target_email = original_email if original_email else new_email
        if not stored_code_info or stored_code_info.get('code') != verification_code or stored_code_info.get('email') != target_email: flash("❌ 电子邮箱更新失败！原因：验证码错误或无效。", category="error"); return redirect(url_for('user.profile_page'))
        if time.time() - stored_code_info.get('timestamp', 0) > 300: flash("❌ 电子邮箱更新失败！原因：验证码已过期，请重试。", category="error"); return redirect(url_for('user.profile_page'))
        email_count = query('SELECT count(*) FROM user WHERE email = %s', [new_email], 'select')
        if email_count and email_count[0][0] > 0: flash("❌ 电子邮箱更新失败！原因：该邮箱已被其他用户注册。", category="error"); return redirect(url_for('user.profile_page'))
        query("UPDATE user SET email = %s WHERE username = %s", [new_email, username]); session.pop('verification_code', None)
        if is_ajax:
            return jsonify({'success': True, 'message': '个人资料（包括电子邮箱）更新成功！', 'avatar_updated': avatar_updated, 'avatar_url': avatar_url_value})
        flash('✅ 个人资料（包括电子邮箱）更新成功！', 'success'); return redirect('/user/profile')
    if is_ajax:
        return jsonify({'success': True, 'message': '个人资料更新成功！', 'avatar_updated': avatar_updated, 'avatar_url': avatar_url_value})
    flash('✅ 个人资料更新成功！', 'success'); return redirect('/user/profile')
@ub.route('/password/update', methods=['POST'])
def update_password():
    username = session.get('username')
    if not username: flash("会话已过期，请重新登录", "warning"); return redirect('/user/login')
    old_password = request.form.get('old_password', ''); new_password = request.form.get('new_password', ''); confirm_password = request.form.get('confirm_password', ''); verification_code = request.form.get('verification_code', '')
    if not all([old_password, new_password, confirm_password]): flash("⚠️ 所有密码字段均为必填项！", "warning"); return redirect('/user/profile')
    user_info = get_current_user_info(username); user_email = user_info.get('email'); stored_code_info = session.get('verification_code')
    if not stored_code_info or stored_code_info.get('code') != verification_code or stored_code_info.get('email') != user_email: flash("❌ 密码更新失败！原因：邮箱验证码错误或已过期。", category="error"); return redirect(url_for('user.profile_page'))
    if time.time() - stored_code_info.get('timestamp', 0) > 300: flash("❌ 密码更新失败！原因：邮箱验证码已过期，请重新获取。", category="error"); return redirect(url_for('user.profile_page'))
    if new_password != confirm_password: flash("❌ 密码更新失败：两次输入的新密码不一致。", "error"); return redirect('/user/profile')
    if len(new_password) < 8 or not re.search(r'\d', new_password) or not re.search(r'[A-Za-z]', new_password): flash("⚠️ 新密码强度不足（至少 8 位，包含字母和数字）", "warning"); return redirect('/user/profile')
    user_data = query("SELECT password FROM user WHERE username = %s LIMIT 1", [username], 'select')
    if not user_data: flash("❌ 用户不存在。", "error"); return redirect('/user/profile')
    stored_hash = user_data[0][0] or '';
    if not check_password_hash(stored_hash, old_password): flash("❌ 密码更新失败：旧密码不正确。", "error"); return redirect('/user/profile')
    session.pop('verification_code', None); new_hashed = generate_password_hash(new_password, method='pbkdf2:sha256'); query("UPDATE user SET password = %s WHERE username = %s", [new_hashed, username]); flash("✅ 密码更新成功！", "success"); return redirect('/user/profile')
@ub.route('/send-verification-code', methods=['POST'])
def send_verification_code():
    email = request.json.get('email', '').strip()
    if not email: return jsonify({'success': False, 'message': '邮箱地址不能为空'}), 400
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email): return jsonify({'success': False, 'message': '无效的邮箱格式'}), 400
    code = f"{random.randint(0, 999999):06d}"
    session['verification_code'] = { 'code': code, 'email': email, 'timestamp': time.time() }
    try:
        msg = Message(subject="[情感分析平台] - 邮箱验证码", recipients=[email], html=f"""<p>您的验证码是：<strong style="font-size: 18px; color: #007bff;">{code}</strong></p><p>此验证码将在5分钟后失效。</p>""", charset='utf-8')
        mail.send(msg); return jsonify({'success': True, 'message': '验证码已发送，请注意查收。'})
    except Exception as e: print(f"邮件发送失败: {e}"); return jsonify({'success': False, 'message': '邮件发送失败，请稍后重试或联系管理员'}), 500
@ub.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('forgot_password_portal.html')
    email = request.form.get('email', '').strip()
    user_data = query("SELECT username FROM user WHERE email = %s LIMIT 1", [email], 'select')
    if user_data:
        token = get_serializer().dumps(email, salt='password-reset-salt'); reset_url = url_for('user.reset_with_token', token=token, _external=True)
        msg = Message(subject="[情感分析平台] - 密码重置请求", recipients=[email], html=f"""<p>请点击链接重置密码：<a href="{reset_url}">{reset_url}</a></p><p>此链接将在30分钟后失效。</p>""", charset='utf-8')
        mail.send(msg)
    flash("邮件发送成功||如果该邮箱已注册，我们已发送密码重置链接。", "success"); return redirect(url_for('user.login'))
@ub.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_with_token(token):
    try:
        email = get_serializer().loads(token, salt='password-reset-salt', max_age=1800)
    except (SignatureExpired, BadTimeSignature):
        flash("密码重置链接无效或已过期||请重新发起找回密码流程。", "error")
        return redirect(url_for('user.forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        if new_password != confirm_password:
            flash("密码更新失败||两次输入的新密码不一致。", "error")
            return render_template('reset_password.html', token=token)
        if len(new_password) < 8 or not re.search(r'\d', new_password) or not re.search(r'[A-Za-z]', new_password):
            flash("密码更新失败||新密码需至少8位并包含字母、数字。", "warning")
            return render_template('reset_password.html', token=token)
        new_hashed = generate_password_hash(new_password, method='pbkdf2:sha256')
        query("UPDATE user SET password = %s WHERE email = %s", [new_hashed, email])
        flash("密码已成功重置||现在可以使用新密码登录。", "success")
        return redirect(url_for('user.login'))

    return render_template('reset_password.html', token=token)
@ub.route('/login-with-code', methods=['POST'])
def login_with_code():
    email = request.form.get('email', '').strip(); verification_code = request.form.get('verification_code', '').strip()
    if not email or not verification_code: flash("⚠️ 邮箱和验证码不能为空！", category="warning"); return redirect('/user/login')
    stored_code_info = session.get('verification_code')
    if not stored_code_info or stored_code_info.get('code') != verification_code or stored_code_info.get('email') != email: flash("❌ 登录失败！原因：邮箱验证码错误或已过期。", category="error"); return redirect('/user/login')
    if time.time() - stored_code_info.get('timestamp', 0) > 300: flash("❌ 登录失败！原因：邮箱验证码已过期，请重新获取。", category="error"); return redirect('/user/login')
    user_data = query("SELECT username, status, ban_reason, ban_details FROM user WHERE email = %s LIMIT 1", [email], 'select')
    if not user_data:
        flash("❌ 登录失败：该邮箱未注册。", category="error"); return redirect('/user/login')
    username, status, ban_reason, ban_details = user_data[0]
    if status == 'disabled':
        _push_ban_notice(ban_reason, ban_details)
        flash('账户访问受限||您的账户已被禁用，请点击申诉按钮或联系管理员。', 'error')
        return redirect('/user/login')
    session.pop('verification_code', None); session['username'] = username; flash('登录成功||欢迎回来，{}！'.format(username), 'success'); return redirect('/page/home')
