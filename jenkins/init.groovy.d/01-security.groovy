import jenkins.model.*
import hudson.security.*

Jenkins instance = Jenkins.get()

def adminUser = System.getenv('JENKINS_ADMIN_ID') ?: 'admin'
def adminPass = System.getenv('JENKINS_ADMIN_PASSWORD') ?: 'admin123'

if (!(instance.getSecurityRealm() instanceof HudsonPrivateSecurityRealm)) {
  def realm = new HudsonPrivateSecurityRealm(false)
  realm.createAccount(adminUser, adminPass)
  instance.setSecurityRealm(realm)
}

def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
strategy.setAllowAnonymousRead(false)
instance.setAuthorizationStrategy(strategy)
instance.save()

println("Jenkins configured with local admin user: ${adminUser}")
