#!/usr/bin/env python3

"""
generate_jenkinsfile.py
Author: b.wangsutthitham (@natebwangsut), atisak klammeng , a.akkaraneewong
-
Generate the Jenkinsfile for each environment.
"""

import requests
import xml.etree.ElementTree
import openpyxl
import json
import subprocess
import os
import time
import random
import sys
from mako.template import Template

################################################################################
# Main                                                                         #
################################################################################

def get_jenkins_xml(jenkins_url):
    #http_proxy="http://dproxy2.scb.co.th:8080"
    #proxyDict={"https": http_proxy, "http": http_proxy, }

    urls =jenkins_url+"config.xml"
    r = requests.get(
        url=urls,
        auth=(username,password),
        #proxies=proxyDict

    )
    print(r)
    return r

def post_jenkins_xml(jenkins_url, config_data):
    #http_proxy="http://dproxy2.scb.co.th:8080"
    #proxyDict={"https": http_proxy, "http": http_proxy }


    urls = jenkins_url+"config.xml"
    p = requests.post(
        url=urls,
        data=config_data,
        auth=(username,password),
     #   proxies=proxyDict

    )
    print(p)

def get_list_job(jenkinurl):


    #http_proxy="http://dproxy2.scb.co.th:8080"
    #proxyDict={"https": http_proxy, "http": http_proxy, }

    g = requests.get(
        url=jenkinurl,
        auth=(
        username,password)
        #proxies=proxyDict
    )
    print(g)
    return g


def check_jenkins_env(env):
    if env == "sit":
        jenkinsurl = 'https://gitlab.easy2easiest.com/jenkins/view/SIT/job/sit-microservices/api/json?pretty=true'
    elif env == "uat":
        jenkinsurl = 'https://gitlab.easy2easiest.com/jenkins/view/UAT/job/uat-racf-team-microservices/api/json?pretty=true'
    elif env == "ps":
        jenkinsurl = 'https://gitlab.easy2easiest.com/jenkins/view/PRODSPT/job/prodspt-racf-team-microservices/api/json?pretty=true'
    elif env == "pt":
        jenkinsurl = 'https://gitlab.easy2easiest.com/jenkins/view/PRODSPT/job/pt/api/json?pretty=true'
    return jenkinsurl


def set_value_all_Jenkins_job(microservice,job_name_url,name_env):

    if name_env == "sit":
        split_nameservice = "-maven-release"
        name_ms_in_url = job_name_url['name'].split(split_nameservice)[0]
    elif  name_env == "uat":
        split_nameservice = "uat-"
        name_ms_in_url =job_name_url['name'].split(split_nameservice)[-1]
    elif  name_env == "ps":
        split_nameservice = "ps-"
        name_ms_in_url =job_name_url['name'].split(split_nameservice)[-1]
    elif  name_env == "pt":
        split_nameservice = "preprod-"
        name_ms_in_url = job_name_url['name'].split(split_nameservice)[-1]

    if name_ms_in_url == microservice:
        print("Original Jobname: " + job_name_url['url'])
        job_url = job_name_url['url'].replace("devops","gitlab")
        job_url = job_url.replace("10.10.2.50", "gitlab.easy2easiest.com")
        job_url = job_url.replace("http://", "https://")
        print(">>>>>>>>>>>>>>>>>>>", job_url)
    else:
        job_url = ""


    return job_url

def edit_config_xml(xml_config,microservice,release_version,md5):
    #print(xml_config.text)
    #print("XML >>> Get xml from jenkins job <<<")
    et = xml.etree.ElementTree.fromstring(xml_config.text)
    for e in et.findall(".//hudson.model.StringParameterDefinition"):

        if microservice=="lookup-migration":
            release_version_split = release_version.split("\n")
            #print(release_version_split[0],release_version_split[1])
            if e.find('name').text == "releaseVersion":
                e.find('defaultValue').text = release_version_split[0].split("=")[-1]
            elif e.find('name').text == "lookupVersion":
                e.find('defaultValue').text = release_version_split[1].split("=")[-1]

        elif microservice=="config-migration":
            e.find('defaultValue').text = release_version.replace(u'\u200b','')

        else:
            if e.find('name').text == "releaseVersion":
                e.find('defaultValue').text = release_version
            elif e.find('name').text == "md5":
                e.find('defaultValue').text = md5

    config_data = xml.etree.ElementTree.tostring(et, encoding='utf8', method='xml').decode()

    return config_data


def download_jar(microservice,release_version):
    showtext=""
    if microservice == "biller-update-batch":
        microservice = "billerbatch"
    elif microservice == "bulk-register":
        microservice = "bulk"
    elif microservice == "cardlessatm":
        microservice = "cardless-atm"
    elif microservice == "eureka":
        microservice = "eureka-peer"
    elif microservice == "lookup":
        microservice = "lookup2"
    elif microservice == "ruleengine":
        microservice = "Rule-Engine"
    elif microservice == "lookup-migration":
        microservice = "data-migration"
        release_version = release_version.split("Release=")[-1]
    micro = microservice + ":" + release_version
    nameArtifact = "-Dartifact=th.co.scb:" + micro

    subprocess.call(["/home/jenkins/tools/hudson.tasks.Maven_MavenInstallation/M3/bin/mvn","dependency:get","-B",nameArtifact])
    try:
        sha1_microservice = subprocess.check_output(["sha1sum","/home/jenkins/.m2/repository/th/co/scb/"+microservice+"/"+release_version+"/"+microservice+"-"+release_version+".jar"])
        showtext = micro+str(sha1_microservice)
        print(showtext)
    except:
        print("no service name")
    return showtext


if __name__ == "__main__":


    ###### in put parameter from python script run as jenkinsfile by env
    username = sys.argv[1]
    password = sys.argv[2]
    name_env = sys.argv[3]
    ####################################################################
    ###### get list of jenkins job from jenkins env ############

    ## check jenkins list by env
    jenkinsurl = check_jenkins_env(name_env)

    ## list all job in jenkins
    list_all_job = get_list_job(jenkinsurl)
    datastore = json.loads(list_all_job.text)
    ###########################################################

    ## read excel file
    xlsx_file = openpyxl.load_workbook(name_env+".xlsx")
    ws = xlsx_file.active
    ## skipped title row
    skipped_firstrow = 0


    microservice_lists_sha1 = list()

    for row in ws.rows:

        ### read data by row from excel file
        microservice = row[0].value
        release_version = row[1].value
        md5 = row[2].value
        #######################################

        if microservice == None:
            break
        if not skipped_firstrow:
            skipped_firstrow+=1
            continue
        if release_version=="-":
            continue

        release_version = release_version.replace(u'\u200b','')

        print("Name Microservice >> ", microservice, "  Release Version >> ", release_version)

        for job_url_index in datastore['jobs']:
            # print(job_url_index)
            ##########################################################################

            # set url compare MS name and Url jenkins
            # return job url

            job_url = set_value_all_Jenkins_job(microservice,job_url_index,name_env)

            ##########################################################################
            if job_url != "":

                # get xml from jenkins job
                # the xml is configuretion from jenkin

                all_of_cofig_job = get_jenkins_xml(job_url)

                # edit configuretion the configuretion come from excel
                config_data = edit_config_xml(all_of_cofig_job,microservice,release_version,md5)

                # post the new configuretion to the jenkins job
                post_jenkins_xml(job_url,config_data)
                if microservice =="config-migration":
                    continue

                # download the jar file and add md5 value to list
                microservice_and_md5 = download_jar(microservice,release_version)
                if microservice_and_md5 != "":
                    microservice_lists_sha1.append(microservice_and_md5)
            else:
                continue

        time.sleep(2)


    # show data all of lists to jenkinis console
    for sha1 in microservice_lists_sha1:
        formatted_sha = sha1.split(" ")[0].split("b'")
        print("sha: %40s %-30s %-20s" % (
            formatted_sha[-1],
            formatted_sha[0].split(":")[0],
            formatted_sha[0].split(":")[-1]))


    print("")
    print("Number of Microservices deployment ",len(microservice_lists_sha1))
