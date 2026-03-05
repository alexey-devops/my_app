import jenkins.model.Jenkins
import org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject
import com.cloudbees.hudson.plugins.folder.computed.PeriodicFolderTrigger

Jenkins instance = Jenkins.get()

def mbJobName = (System.getenv('JENKINS_MULTIBRANCH_JOB') ?: 'my-app-mb').trim()
def scanInterval = (System.getenv('JENKINS_MULTIBRANCH_SCAN_INTERVAL') ?: '2m').trim()

def job = instance.getItemByFullName(mbJobName)
if (!(job instanceof WorkflowMultiBranchProject)) {
  println("Multibranch trigger setup skipped: '${mbJobName}' not found")
  return
}

def mb = (WorkflowMultiBranchProject) job
def existing = mb.getTriggers().values().find { it instanceof PeriodicFolderTrigger }
def needsUpdate = (existing == null) || (existing.getInterval() != scanInterval)

if (needsUpdate) {
  if (existing != null) {
    mb.removeTrigger(existing)
  }
  mb.addTrigger(new PeriodicFolderTrigger(scanInterval))
  mb.save()
  println("Configured periodic multibranch scan for '${mbJobName}' with interval '${scanInterval}'")
} else {
  println("Periodic multibranch scan already configured for '${mbJobName}' (${scanInterval})")
}
