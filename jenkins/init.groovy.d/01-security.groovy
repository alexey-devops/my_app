import jenkins.model.*
import hudson.security.*
import hudson.model.User
import java.util.UUID

Jenkins instance = Jenkins.get()

def adminUser = System.getenv('JENKINS_ADMIN_ID') ?: 'admin'
def adminPass = System.getenv('JENKINS_ADMIN_PASSWORD')
if (!adminPass?.trim()) {
  adminPass = UUID.randomUUID().toString()
  println("JENKINS_ADMIN_PASSWORD is not set. Generated one-time admin password: ${adminPass}")
}

if (!(instance.getSecurityRealm() instanceof HudsonPrivateSecurityRealm)) {
  def realm = new HudsonPrivateSecurityRealm(false)
  instance.setSecurityRealm(realm)
}

def realm = (HudsonPrivateSecurityRealm) instance.getSecurityRealm()
if (User.getById(adminUser, false) == null) {
  realm.createAccount(adminUser, adminPass)
}

def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
strategy.setAllowAnonymousRead(false)
instance.setAuthorizationStrategy(strategy)
instance.save()

println("Jenkins configured with local admin user: ${adminUser}")
