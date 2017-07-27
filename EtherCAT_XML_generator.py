#!/usr/bin/python3.5

# README
# GPL

##########################################################################
# DEPENDENCIES
##########################################################################

# xmldict: python3-xmltodict under Debian/Ubuntu
import xmltodict

from collections import OrderedDict


##########################################################################
# FUNCTIONS
##########################################################################

#_________________________________________________________________________
# Customise the Master node
def buildMasterNode(Master, config):
	# Modify Info -> Source
	# How?

	return Master


#_________________________________________________________________________
# Customise the Cyclic node
def buildCyclicNode(Cyclic, config):
	return Cyclic


#_________________________________________________________________________
# Customise the ProcessImage node
def buildProcessImageNode(ProcessImage, config):
	return ProcessImage


#_________________________________________________________________________
# Customise Slave nodes
def buildSlaveNode(Slave, i, config):
	# Main Slave node shorthand
	s = Slave['Slave']

	# Modify Info node
	s['Info']['Name']		= 'Box ' + str(i+1)
	s['Info']['PhysAddr']		= int(s['Info']['PhysAddr']) + i
	s['Info']['AutoIncAddr']	= (65536 - i) % 65536
	
	# Modify ProcessData node
	s['ProcessData']['Send']['BitStart'] = int(s['ProcessData']['Send']['BitStart']) + i * int(s['ProcessData']['Send']['BitLength'])
	s['ProcessData']['Recv']['BitStart'] = int(s['ProcessData']['Recv']['BitStart']) + i * int(s['ProcessData']['Recv']['BitLength'])

	# Modify InitCmds
	# ...
	
	# Set main slave node back into Slave object
	Slave['Slave'] = s

	return Slave


##########################################################################
# MAIN
##########################################################################

#_________________________________________________________________________
# Main function
def main():
	#_________________________________________________________________________
	# Configuration of the to be generated EtherCAT Network Information (ENI)
	# (*.xml) file

	config = {	
		'slaves':	{	'N': 3,
					'types': [	'Slave_phil_boards',
							'Slave_phil_boards',
							'Slave_phil_boards'	]
				}
	}


	#_________________________________________________________________________
	# Generate main <EtherCATConfig> and <Config> nodes

	# Generate eni dict from EtherCATConfig.xml
	f = open('templates/EtherCATConfig.xml')
	ENI = xmltodict.parse(f.read())
	f.close()


	#_________________________________________________________________________
	# Add <Master> node

	f = open('templates/Master.xml')
	Master = xmltodict.parse(f.read())
	f.close()

	# Customise node
	Master = buildMasterNode(Master, config)

	# Add as child of Config
	ENI['EtherCATConfig']['Config'] = Master


	#_________________________________________________________________________
	# Add <Slave> nodes

	# Build list of Slave nodes
	Slaves = []
	for i in range(0, config['slaves']['N']):
		# Get slave template and add to Slaves
		f = open('templates/' + config['slaves']['types'][i] + '.xml')
		Slave = xmltodict.parse(f.read())
		f.close()

		# Customise node
		Slave = buildSlaveNode(Slave, i, config)

		# Append slave node
		Slaves.append(Slave['Slave'])

	# Merge OrderedDicts
	# See https://stackoverflow.com/questions/38987/how-to-merge-two-python-dictionaries-in-a-single-expression
	ENI['EtherCATConfig']['Config'] = OrderedDict(ENI['EtherCATConfig']['Config'], **{'Slave': Slaves})


	#_________________________________________________________________________
	# Add <Cyclic> node

	f = open('templates/Cyclic.xml')
	Cyclic = xmltodict.parse(f.read())
	f.close()

	# Customise node
	Cyclic = buildCyclicNode(Cyclic, config)

	# Add as child of Config
	ENI['EtherCATConfig']['Config'] = OrderedDict(ENI['EtherCATConfig']['Config'], **Cyclic)


	#_________________________________________________________________________
	# Add <ProcessImage> node

	f = open('templates/ProcessImage.xml')
	ProcessImage = xmltodict.parse(f.read())
	f.close()

	# Customise node
	ProcessImage = buildProcessImageNode(ProcessImage, config)

	# Add as child of Config
	ENI['EtherCATConfig']['Config'] = OrderedDict(ENI['EtherCATConfig']['Config'], **ProcessImage)


	#_________________________________________________________________________
	# Output

	print("Writing result to ENI.xml..")
	fout = open("ENI.xml", 'w')
	fout.write(xmltodict.unparse(ENI, pretty=True))
	fout.close()


#_________________________________________________________________________
# Execute only if run as a script
if __name__ == "__main__":
    main()


