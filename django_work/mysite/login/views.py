from django.shortcuts import render
from django.shortcuts import redirect, reverse
from .models import User, ConfirmString
from .forms import UserForm, RegisterForm
import hashlib
import datetime
from django.conf import settings


# Create your views here.

def hash_code(s, salt='mysite'):
    h = hashlib.sha256()
    s += salt
    h.update(s.encode())
    return h.hexdigest()


def index(request):
    pass
    return render(request, 'login/index.html')


'''
def login(request):
    if request.method == 'POST':
        username = request.POST.get('username',None)
        password = request.POST.get('password',None)
        if username and password:
            username = username.strip()
            # 密码验证
            # 邮箱验证
            # 。。。
            try:
                user = User.objects.get(name=username)

            except:
                message = '用户名不正确'
                return render(request,'login/login.html',{'message':message})
            else:
                print(user.name, user.password)
                return redirect('/login/')
    return render(request, 'login/login.html')
'''


def login(request):
    if request.session.get('is_login', None):
        return redirect('/login/')
    if request.method == 'POST':
        login_form = UserForm(request.POST)
        message = '请检查填写的内容'
        if login_form.is_valid():
            username = login_form.cleaned_data['username']
            password = login_form.cleaned_data['password']
            try:
                user = User.objects.get(name=username)
                if not user.has_confirmed:
                    message = '该用户还未通过邮件确认'
                    return render(request, 'login/login.html', locals())
                if user.password == hash_code(password):
                    # 你完全可以往里面写任何数据，不仅仅限于用户相关！
                    request.session['is_login'] = True
                    request.session['user_id'] = user.id
                    request.session['user_name'] = user.name
                    return redirect('/login/')
                else:
                    message = '密码不正确'
            except:
                message = '用户不存在!'

        return render(request, 'login/login.html', locals())

    login_form = UserForm()

    return render(request, 'login/login.html', locals())


def register(request):
    if request.session.get('is_login', None):
        return render(request, '/login/')
    if request.method == 'POST':
        register_form = RegisterForm(request.POST)
        message = '请检查输入的信息'
        if register_form.is_valid():
            username = register_form.cleaned_data['username']
            password1 = register_form.cleaned_data['password1']
            password2 = register_form.cleaned_data['password2']
            email = register_form.cleaned_data['email']
            sex = register_form.cleaned_data['sex']
            if password1 != password2:
                message = '两次输入的密码不一样'
                return render(request, 'login/register.html', locals())
            else:
                same_user_name = User.objects.filter(name=username)
                if same_user_name:
                    message = '用户名重复'
                    return render(request, 'login/register.html', locals())
                same_user_email = User.objects.filter(email=email)
                if same_user_email:
                    message = '邮件地址已经注册！'
                    return render(request, 'login/register.html', locals())

                new_user = User()
                new_user.name = username
                new_user.password = hash_code(password2)
                new_user.email = email
                new_user.sex = sex
                new_user.save()

                code = make_confirm_string(new_user)
                send_email(email, code)

                message = '请前往注册邮箱，进行邮件确认！'
                return render(request, 'login/confirm.html', locals())  # 跳转到等待邮件确认页面。

    register_form = RegisterForm()
    return render(request, 'login/register.html', locals())


def user_confirm(request):
    code = request.GET.get('code', None)

    message = ''

    try:
        confirm = ConfirmString.objects.get(code=code)
    except:
        message = '无效的确认请求'
        return render(request, 'login/confirm.html', locals())

    c_time = confirm.c_time
    now = datetime.datetime.now()
    if now > c_time + datetime.timedelta(days=settings.CONFIRM_DAYS):
        confirm.user.delete()
        message = '您的邮件已经过期！请重新注册！'
        return render(request, 'login/confirm.html', locals())

    else:
        confirm.user.has_confirmed = True
        confirm.user.save()
        confirm.delete()
        message = '感谢确认,请使用账户登录'
        return render(request, 'login/confirm.html', locals())


def logout(request):
    if not request.session.get('is_login', None):
        # 如果没有登录就不用登出
        return redirect('/login/')
    request.session.flush()
    # 或者使用下面的方法
    # del request.session['is_login']
    # del request.session['user_id']
    # del request.session['user_name']
    return redirect("/login/")


def make_confirm_string(user):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    code = hash_code(user.name, now)
    ConfirmString.objects.create(code=code, user=user, )
    return code


def send_email(email, code):
    from django.core.mail import EmailMultiAlternatives

    subject = '来自www.liujingfu.com的注册确认邮件'

    text_content = '''你好 我是刘 如果看到这段信息 说明你的邮箱服务器不支持
    HTML链接功能请联系管理员'''

    html_content = '''
              <p>感谢注册<a href="http://{}/confirm/?code={}" target=blank>www.liujiangblog.com</a>，\
                    这里是刘</p>
                    <p>请点击站点链接完成注册确认！</p>
                    <p>此链接有效期为{}天！</p>'''.format('127.0.0.1:8000', code, settings.CONFIRM_DAYS)

    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])

    msg.attach_alternative(html_content, 'text/html')
    msg.send()
