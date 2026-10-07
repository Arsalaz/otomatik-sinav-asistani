// Firebase Config
const firebaseConfig = {
  apiKey: "AIzaSyC2p1uvYNF75Q6va5H_eRBm_MNfrxN4lyU",
  authDomain: "eduai-sinav.firebaseapp.com",
  projectId: "eduai-sinav",
  storageBucket: "eduai-sinav.firebasestorage.app",
  messagingSenderId: "663810168320",
  appId: "1:663810168320:web:3cce078ce22641d54f6ae5",
  measurementId: "G-9H49Z6Y8FN"
};

// Initialize Firebase (Compat)
if (!firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
}

const db = firebase.firestore();

// Arayüz (Rol Seçimi) Mantığı
const btnTeacher = document.getElementById('btnTeacher');
const btnStudent = document.getElementById('btnStudent');
const loginForm = document.getElementById('loginForm');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const loginBtn = document.getElementById('loginBtn');
const registerBtn = document.getElementById('registerBtn');

let selectedRole = 'teacher';

if(btnTeacher && btnStudent) {
    btnTeacher.addEventListener('click', () => {
        btnTeacher.classList.add('active');
        btnStudent.classList.remove('active');
        selectedRole = 'teacher';
    });

    btnStudent.addEventListener('click', () => {
        btnStudent.classList.add('active');
        btnTeacher.classList.remove('active');
        selectedRole = 'student';
    });
}

// Giriş Yap İşlemi
if(loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = emailInput.value;
        const password = passwordInput.value;
        
        loginBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Bekleyin...';
        loginBtn.disabled = true;

        try {
            const userCred = await firebase.auth().signInWithEmailAndPassword(email, password);
            const user = userCred.user;
            
            // Firestore'dan rolü çek (Güvenli yöntem)
            const doc = await db.collection("users").doc(user.uid).get();
            if (doc.exists) {
                const role = doc.data().role;
                if (role === 'teacher') {
                    window.location.href = "teacher.html";
                } else {
                    window.location.href = "student.html";
                }
            } else {
                alert("Veritabanında rolünüz bulunamadı. Lütfen yeni hesap oluşturun.");
                firebase.auth().signOut();
                loginBtn.innerHTML = 'Giriş Yap <i class="fa-solid fa-arrow-right-to-bracket"></i>';
                loginBtn.disabled = false;
            }
        } catch (error) {
            console.error("Giriş Hatası:", error);
            alert("Giriş başarısız! E-posta veya şifre hatalı olabilir.");
            loginBtn.innerHTML = 'Giriş Yap <i class="fa-solid fa-arrow-right-to-bracket"></i>';
            loginBtn.disabled = false;
        }
    });
}

// Kayıt Ol İşlemi
if(registerBtn) {
    registerBtn.addEventListener('click', async () => {
        const email = emailInput.value;
        const password = passwordInput.value;

        if(!email || !password || password.length < 6) {
            alert("Lütfen e-posta adresinizi girin ve şifrenizin en az 6 haneli olduğundan emin olun.");
            return;
        }

        registerBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Kaydediliyor...';
        registerBtn.disabled = true;

        try {
            const userCred = await firebase.auth().createUserWithEmailAndPassword(email, password);
            const user = userCred.user;
            
            // Firestore'a kalıcı olarak kaydet
            await db.collection("users").doc(user.uid).set({
                email: email,
                role: selectedRole,
                createdAt: firebase.firestore.FieldValue.serverTimestamp()
            });

            alert("Hesabınız başarıyla oluşturuldu! Sisteme yönlendiriliyorsunuz.");
            if (selectedRole === 'teacher') {
                window.location.href = "teacher.html";
            } else {
                window.location.href = "student.html";
            }
        } catch (error) {
            console.error("Kayıt Hatası:", error);
            if(error.code === 'auth/email-already-in-use') {
                alert("Bu e-posta adresi zaten kullanılıyor.");
            } else {
                alert("Kayıt oluşturulurken bir hata oluştu: " + error.message);
            }
            registerBtn.innerHTML = 'Yeni Hesap Oluştur';
            registerBtn.disabled = false;
        }
    });
}

// Oturum durumunu dinle (Sadece login sayfasındayken, yönlendirme için)
firebase.auth().onAuthStateChanged(async (user) => {
    if (user && window.location.pathname.includes('login.html')) {
        const doc = await db.collection("users").doc(user.uid).get();
        if(doc.exists) {
            if(doc.data().role === 'teacher') window.location.href = "teacher.html";
            else window.location.href = "student.html";
        }
    }
});
